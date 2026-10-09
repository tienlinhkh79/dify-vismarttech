"""Backfill Zalo OA conversation history into omnichannel inbox."""

from __future__ import annotations

import logging
from typing import Any

from services.omnichannel.zalo_bridge_job_service import ZaloBridgeJobService
from services.omnichannel.zalo_oa_classify import classify_oa_webhook_event, is_self_oa_event
from services.omnichannel.zalo_oa_history_client import get_conversation_messages, list_recent_chat
from services.omnichannel.zalo_runtime_service import ZaloRuntimeService

logger = logging.getLogger(__name__)


class ZaloOaBackfillService:
    @classmethod
    def enqueue_channel_backfill(cls, *, channel_id: str, user_id: str | None = None) -> bool:
        dedup = f"{channel_id}:backfill:{user_id or 'all'}"
        return ZaloBridgeJobService.enqueue(
            channel_id=channel_id,
            kind="backfill",
            dedup_key=dedup[:512],
            payload={"user_id": user_id},
        )

    @classmethod
    def run_job_payload(
        cls,
        *,
        channel_id: str,
        payload: dict[str, Any],
        channel_config: dict[str, Any],
    ) -> int:
        token = str(channel_config.get("oa_access_token") or "").strip()
        oa_id = str(channel_config.get("oa_id") or "").strip()
        if not token or not oa_id:
            return 0

        target_user = (payload.get("user_id") or "").strip() or None
        user_ids: list[str] = []
        if target_user:
            user_ids = [target_user]
        else:
            chats = list_recent_chat(access_token=token, oa_id=oa_id, offset=0, count=30)
            user_ids = [c["user_id"] for c in chats if c.get("user_id")]

        imported = 0
        for uid in user_ids:
            messages = get_conversation_messages(access_token=token, user_id=uid, offset=0, count=50)
            for raw in reversed(messages):
                event_name = str(raw.get("event_name") or raw.get("type") or "").strip()
                if not event_name:
                    continue
                if not (event_name.startswith("user_send_") or is_self_oa_event(event_name)):
                    continue
                synthetic = {
                    "event_name": event_name,
                    "sender": raw.get("from_id") == oa_id and {"id": oa_id} or {"id": uid},
                    "recipient": raw.get("from_id") == oa_id and {"id": uid} or {"id": oa_id},
                    "message": {
                        "text": raw.get("message") or raw.get("text") or "",
                        "msg_id": raw.get("message_id") or raw.get("msg_id"),
                        "attachments": raw.get("attachments") or [],
                    },
                    "oa_id": oa_id,
                    "timestamp": raw.get("time") or raw.get("timestamp"),
                }
                event = classify_oa_webhook_event(
                    channel_id,
                    synthetic,
                    is_self=is_self_oa_event(event_name),
                )
                if not event:
                    continue
                imported += ZaloRuntimeService.process_events(channel_id, [event], channel_config)
        return imported
