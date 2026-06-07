"""OA 48h consultation window tracker (ported from zca-bridge consultationWindow.ts + consultationTracker.ts)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import TypedDict

from extensions.ext_redis import redis_client
from libs.datetime_utils import naive_utc_now
from models.trigger import OmniChannelMessageDirection, OmniChannelMessageSource
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService

logger = logging.getLogger(__name__)

WINDOW_HOURS = 48
FREE_LIMIT = 8
NEAR_LIMIT_AT = 6

_OUT_OF_WINDOW_NOTE = (
    "⚠️ Ngoài cửa sổ 48h tư vấn (user chưa nhắn lại gần đây) — tin này có thể bị Zalo tính phí hoặc chặn. (ước tính)"
)
_LIMIT_REACHED_NOTE = (
    "⚠️ Đã dùng hết 8 tin tư vấn miễn phí trong kỳ 48h — các tin tiếp theo có thể bị tính phí. (ước tính)"
)


class _WindowState(TypedDict):
    last_inbound_at: str | None
    sent_count: int


def _near_limit_note(count: int) -> str:
    return f"ℹ️ Đã dùng {count}/{FREE_LIMIT} tin tư vấn miễn phí trong kỳ 48h. (ước tính)"


def _evaluate(state: _WindowState, now: datetime) -> tuple[int, str | None]:
    last_raw = (state.get("last_inbound_at") or "").strip()
    sent_count = int(state.get("sent_count") or 0)
    last_inbound: datetime | None = None
    if last_raw:
        try:
            last_inbound = datetime.fromisoformat(last_raw)
        except ValueError:
            last_inbound = None
    within = (
        last_inbound is not None
        and (now - last_inbound).total_seconds() <= WINDOW_HOURS * 3600
    )
    if not within:
        return sent_count, _OUT_OF_WINDOW_NOTE
    new_count = sent_count + 1
    warning: str | None = None
    if new_count == FREE_LIMIT:
        warning = _LIMIT_REACHED_NOTE
    elif new_count == NEAR_LIMIT_AT:
        warning = _near_limit_note(new_count)
    return new_count, warning


class ZaloOaConsultationService:
    @staticmethod
    def _redis_key(channel_id: str, user_id: str) -> str:
        return f"zalo:consult:{channel_id}:{user_id}"

    @classmethod
    def _load_state(cls, channel_id: str, user_id: str) -> _WindowState:
        raw = redis_client.get(cls._redis_key(channel_id, user_id))
        if not raw:
            return {"last_inbound_at": None, "sent_count": 0}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {
                    "last_inbound_at": parsed.get("last_inbound_at"),
                    "sent_count": int(parsed.get("sent_count") or 0),
                }
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return {"last_inbound_at": None, "sent_count": 0}

    @classmethod
    def _save_state(cls, channel_id: str, user_id: str, state: _WindowState) -> None:
        redis_client.set(
            cls._redis_key(channel_id, user_id),
            json.dumps(state),
            ex=timedelta(days=7),
        )

    @classmethod
    def on_inbound(cls, *, channel_id: str, user_id: str) -> None:
        state: _WindowState = {
            "last_inbound_at": naive_utc_now().isoformat(),
            "sent_count": 0,
        }
        cls._save_state(channel_id, user_id, state)

    @classmethod
    def on_outbound(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        user_id: str,
    ) -> None:
        state = cls._load_state(channel_id, user_id)
        now = naive_utc_now()
        new_count, warning = _evaluate(state, now)
        if new_count != int(state.get("sent_count") or 0):
            state["sent_count"] = new_count
            cls._save_state(channel_id, user_id, state)
        if warning:
            cls._post_system_note(
                tenant_id=tenant_id,
                channel_id=channel_id,
                user_id=user_id,
                content=warning,
                note_type="consultation_warning",
            )

    @staticmethod
    def _post_system_note(
        *,
        tenant_id: str,
        channel_id: str,
        user_id: str,
        content: str,
        note_type: str,
    ) -> None:
        payload: MessageWritePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "external_user_id": user_id,
            "direction": OmniChannelMessageDirection.OUTBOUND,
            "source": OmniChannelMessageSource.SYSTEM,
            "content": content,
            "attachments": [],
            "metadata": {"system_note": True, "system_note_type": note_type},
            "created_at": None,
        }
        try:
            OmnichannelOpsService.record_message(payload)
        except Exception:
            logger.debug("Failed to post consultation note channel=%s", channel_id, exc_info=True)
