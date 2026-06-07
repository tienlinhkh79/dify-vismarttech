"""Ingest Zalo Personal messages forwarded from the optional zca-js worker."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from core.app.entities.app_invoke_entities import InvokeFrom
from models.trigger import (
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
    OmniChannelType,
)
from services.app_generate_service import AppGenerateService
from services.end_user_service import EndUserService
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.channel_management_service import ZALO_PERSONAL_DRAFT_APP_PLACEHOLDER
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService
from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService

logger = logging.getLogger(__name__)


class ZaloPersonalRuntimeService:
    @classmethod
    def process_inbound_event(
        cls,
        *,
        channel_id: str,
        tenant_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event.get("is_self"):
            return None
        thread_id = str(event.get("thread_id") or "").strip()
        if not thread_id:
            logger.warning("Zalo personal inbound missing thread_id channel=%s", channel_id)
            return None
        text = str(event.get("text") or "").strip()
        if not text:
            return None
        sender_name = str(event.get("sender_name") or "").strip()
        external_message_id = str(event.get("message_id") or "").strip() or None
        created_at: datetime | None = None
        ts_raw = event.get("timestamp")
        if ts_raw is not None:
            try:
                ts_num = int(ts_raw)
                if ts_num > 1_000_000_000_000:
                    ts_num //= 1000
                created_at = datetime.utcfromtimestamp(ts_num)
            except (TypeError, ValueError, OSError):
                created_at = None

        payload: MessageWritePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "external_user_id": thread_id,
            "direction": OmniChannelMessageDirection.INBOUND,
            "source": OmniChannelMessageSource.WEBHOOK,
            "content": text,
            "external_message_id": external_message_id,
            "attachments": [],
            "metadata": {},
            "participant_display_name": sender_name or None,
            "participant_profile_pic_url": None,
            "channel_actor_name": None,
            "channel_actor_picture_url": None,
            "created_at": created_at,
        }
        record = OmnichannelOpsService.record_message(payload)
        if record:
            cls._maybe_auto_reply(
                channel_id=channel_id,
                tenant_id=tenant_id,
                thread_id=thread_id,
                text=text,
                record=record,
            )
        return record

    @classmethod
    def _maybe_auto_reply(
        cls,
        *,
        channel_id: str,
        tenant_id: str,
        thread_id: str,
        text: str,
        record: dict[str, Any],
    ) -> None:
        channel_config = ChannelConfigService.get_zalo_personal_channel_config(channel_id)
        if not channel_config:
            return
        dify_app_id = str(channel_config.get("app_id") or "").strip()
        if not dify_app_id or dify_app_id == ZALO_PERSONAL_DRAFT_APP_PLACEHOLDER:
            return
        try:
            app = MessengerRuntimeService._get_reply_app(dify_app_id)
        except Exception:
            logger.exception("Zalo personal auto-reply app lookup failed channel=%s app=%s", channel_id, dify_app_id)
            return

        session_user_id = f"zalo_personal:{channel_id}:{thread_id}"
        end_user = EndUserService.get_or_create_end_user_by_type(
            type=InvokeFrom.SERVICE_API,
            tenant_id=app.tenant_id,
            app_id=app.id,
            user_id=session_user_id,
        )
        workflow_start_inputs: dict[str, str] = {
            OmnichannelAppStartInputKey.CHANNEL_ID: channel_id,
            OmnichannelAppStartInputKey.CHANNEL_TYPE: OmniChannelType.ZALO_PERSONAL.value,
            OmnichannelAppStartInputKey.CONVERSATION_ID: str(record.get("conversation_id") or ""),
            OmnichannelAppStartInputKey.EXTERNAL_USER_ID: thread_id,
        }
        try:
            result = AppGenerateService.generate(
                app_model=app,
                user=end_user,
                args={
                    "inputs": workflow_start_inputs,
                    "query": text,
                    "files": [],
                    "response_mode": "blocking",
                    "auto_generate_name": False,
                },
                invoke_from=InvokeFrom.SERVICE_API,
                streaming=False,
            )
        except Exception:
            logger.exception("Zalo personal auto-reply generation failed channel=%s", channel_id)
            return

        reply_text = result.get("answer") if isinstance(result, dict) else None
        if not isinstance(reply_text, str) or not reply_text.strip():
            return

        try:
            ZaloPersonalSessionService.send_text_message(
                channel_id=channel_id,
                thread_id=thread_id,
                text=reply_text.strip(),
            )
        except Exception:
            logger.exception("Zalo personal auto-reply send failed channel=%s", channel_id)
            return

        outbound_payload: MessageWritePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "external_user_id": thread_id,
            "direction": OmniChannelMessageDirection.OUTBOUND,
            "source": OmniChannelMessageSource.SYSTEM,
            "content": reply_text.strip(),
            "external_message_id": None,
            "attachments": [],
            "metadata": {},
            "participant_display_name": record.get("participant_display_name"),
            "participant_profile_pic_url": None,
            "channel_actor_name": None,
            "channel_actor_picture_url": None,
            "created_at": None,
        }
        OmnichannelOpsService.record_message(outbound_payload)
