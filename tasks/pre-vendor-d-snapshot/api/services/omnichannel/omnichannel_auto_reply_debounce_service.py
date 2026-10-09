"""Debounce omnichannel auto-replies so rapid inbound messages merge into one LLM call."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, TypedDict

from extensions.ext_redis import redis_client

logger = logging.getLogger(__name__)

DEFAULT_DEBOUNCE_SECONDS = 4.0
_REDIS_PREFIX = "omnichannel:auto_reply_debounce"
_REDIS_TTL_SECONDS = 120


class AutoReplyDebounceFragment(TypedDict, total=False):
    channel_type: str
    tenant_id: str
    text: str
    conversation_id: str
    event: dict[str, Any]
    extras: dict[str, Any]


class OmnichannelAutoReplyDebounceService:
    """Wait for a short silence window, merge inbound fragments, then reply once."""

    @classmethod
    def debounce_seconds(cls) -> float:
        return DEFAULT_DEBOUNCE_SECONDS

    @staticmethod
    def _messages_key(channel_id: str, external_user_id: str) -> str:
        return f"{_REDIS_PREFIX}:msgs:{channel_id}:{external_user_id}"

    @staticmethod
    def _last_at_key(channel_id: str, external_user_id: str) -> str:
        return f"{_REDIS_PREFIX}:last_at:{channel_id}:{external_user_id}"

    @classmethod
    def enqueue(
        cls,
        *,
        channel_type: str,
        channel_id: str,
        tenant_id: str,
        external_user_id: str,
        fragment: AutoReplyDebounceFragment,
    ) -> bool:
        """Buffer an inbound auto-reply fragment and schedule a debounced worker."""
        payload: AutoReplyDebounceFragment = {
            "channel_type": channel_type,
            "tenant_id": tenant_id,
            "text": str(fragment.get("text") or "").strip(),
            "conversation_id": str(fragment.get("conversation_id") or "").strip(),
            "event": dict(fragment.get("event") or {}),
            "extras": dict(fragment.get("extras") or {}),
        }
        if not payload["text"] and not (payload["event"].get("attachments")):
            return False

        msgs_key = cls._messages_key(channel_id, external_user_id)
        last_at_key = cls._last_at_key(channel_id, external_user_id)
        now = time.time()
        try:
            pipe = redis_client.pipeline()
            pipe.rpush(msgs_key, json.dumps(payload, ensure_ascii=False))
            pipe.set(last_at_key, str(now), ex=_REDIS_TTL_SECONDS)
            pipe.expire(msgs_key, _REDIS_TTL_SECONDS)
            pipe.execute()
        except Exception:
            logger.exception(
                "Auto-reply debounce enqueue failed channel=%s user=%s",
                channel_id,
                external_user_id,
            )
            return False

        from tasks.omnichannel_tasks import process_debounced_auto_reply

        process_debounced_auto_reply.apply_async(
            args=[channel_id, external_user_id],
            countdown=int(cls.debounce_seconds()),
        )
        return True

    @classmethod
    def process(cls, *, channel_id: str, external_user_id: str) -> str:
        """Drain the buffer when the user has been quiet long enough."""
        last_at_key = cls._last_at_key(channel_id, external_user_id)
        try:
            last_at_raw = redis_client.get(last_at_key)
        except Exception:
            logger.exception(
                "Auto-reply debounce read failed channel=%s user=%s",
                channel_id,
                external_user_id,
            )
            return "redis_error"

        if not last_at_raw:
            return "empty"

        try:
            last_at = float(last_at_raw.decode() if isinstance(last_at_raw, bytes) else last_at_raw)
        except (TypeError, ValueError):
            last_at = 0.0

        debounce = cls.debounce_seconds()
        elapsed = time.time() - last_at
        if elapsed < debounce - 0.05:
            from tasks.omnichannel_tasks import process_debounced_auto_reply

            process_debounced_auto_reply.apply_async(
                args=[channel_id, external_user_id],
                countdown=max(1, int(debounce - elapsed + 0.5)),
            )
            return "rescheduled"

        msgs_key = cls._messages_key(channel_id, external_user_id)
        try:
            raw_items = redis_client.lrange(msgs_key, 0, -1)
            if raw_items:
                redis_client.delete(msgs_key, last_at_key)
        except Exception:
            logger.exception(
                "Auto-reply debounce drain failed channel=%s user=%s",
                channel_id,
                external_user_id,
            )
            return "redis_error"

        if not raw_items:
            return "empty"

        fragments: list[AutoReplyDebounceFragment] = []
        for raw in raw_items:
            try:
                text = raw.decode() if isinstance(raw, bytes) else raw
                item = json.loads(text)
            except (json.JSONDecodeError, UnicodeError):
                continue
            if isinstance(item, dict):
                fragments.append(item)  # type: ignore[arg-type]

        if not fragments:
            return "empty"

        from services.omnichannel.omnichannel_auto_reply_executor import OmnichannelAutoReplyExecutor

        try:
            OmnichannelAutoReplyExecutor.execute_merged(
                channel_id=channel_id,
                external_user_id=external_user_id,
                fragments=fragments,
            )
        except Exception:
            logger.exception(
                "Auto-reply debounce execution failed channel=%s user=%s",
                channel_id,
                external_user_id,
            )
            return "execution_error"
        return "processed"

    @staticmethod
    def merge_texts(fragments: list[AutoReplyDebounceFragment]) -> str:
        parts: list[str] = []
        for fragment in fragments:
            text = str(fragment.get("text") or "").strip()
            if text:
                parts.append(text)
        return "\n".join(parts)
