"""Runtime flow for Zalo OA <-> Dify bidirectional chat."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from core.app.entities.app_invoke_entities import InvokeFrom
from core.helper.ssrf_proxy import ssrf_proxy
from models.trigger import OmniChannelMessageDirection, OmniChannelMessageSource
from services.app_generate_service import AppGenerateService
from services.end_user_service import EndUserService
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey
from services.omnichannel.omnichannel_ops_service import OmnichannelOpsService

logger = logging.getLogger(__name__)


class ZaloRuntimeConfig(TypedDict):
    app_id: str
    oa_access_token: str


class ZaloRuntimeService:
    """Generate and send replies for Zalo OA inbound events."""

    @staticmethod
    def _send_text_reply(recipient_user_id: str, message_text: str, channel_config: ZaloRuntimeConfig) -> None:
        # Zalo OA API endpoint for customer-care text replies.
        endpoint = "https://openapi.zalo.me/v2.0/oa/message"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["oa_access_token"]},
            json={
                "recipient": {"user_id": recipient_user_id},
                "message": {"text": message_text},
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @classmethod
    def process_events(
        cls, channel_id: str, events: list[OmniChannelIncomingEvent], channel_config: ZaloRuntimeConfig
    ) -> int:
        if not events:
            return 0

        app = MessengerRuntimeService._get_reply_app(channel_config["app_id"])
        sent_count = 0
        for event in events:
            recipient_user_id = event["external_user_id"]
            try:
                if not MessengerRuntimeService._should_process_event(channel_id, event):
                    continue

                session_user_id = f"zalo:{channel_id}:{recipient_user_id}"
                end_user = EndUserService.get_or_create_end_user_by_type(
                    type=InvokeFrom.SERVICE_API,
                    tenant_id=app.tenant_id,
                    app_id=app.id,
                    user_id=session_user_id,
                )
                event_query = MessengerRuntimeService._build_event_query(event)
                if not event_query:
                    continue
                record_message_result: dict[str, Any] | None = None
                try:
                    record_message_result = OmnichannelOpsService.record_message(
                        {
                            "tenant_id": app.tenant_id,
                            "channel_id": channel_id,
                            "external_user_id": recipient_user_id,
                            "direction": OmniChannelMessageDirection.INBOUND,
                            "source": OmniChannelMessageSource.WEBHOOK,
                            "content": str(event.get("text") or "").strip(),
                            "external_message_id": event.get("message_id"),
                            "attachments": list(event.get("attachments") or []),
                            "metadata": {"raw_event": event.get("raw_event") or {}},
                            "created_at": None,
                        }
                    )
                except Exception:
                    logger.debug("Failed to persist inbound Zalo message channel=%s", channel_id, exc_info=True)

                workflow_start_inputs: dict[str, str] = {}
                if record_message_result:
                    workflow_start_inputs = {
                        OmnichannelAppStartInputKey.CHANNEL_ID: channel_id,
                        OmnichannelAppStartInputKey.CHANNEL_TYPE: str(record_message_result.get("channel_type") or ""),
                        OmnichannelAppStartInputKey.CONVERSATION_ID: str(record_message_result.get("conversation_id") or ""),
                        OmnichannelAppStartInputKey.EXTERNAL_USER_ID: str(recipient_user_id),
                    }

                result = AppGenerateService.generate(
                    app_model=app,
                    user=end_user,
                    args={
                        "inputs": workflow_start_inputs,
                        "query": event_query,
                        "files": MessengerRuntimeService._build_event_files(event),
                        "response_mode": "blocking",
                        "auto_generate_name": False,
                    },
                    invoke_from=InvokeFrom.SERVICE_API,
                    streaming=False,
                )
                reply_text = result.get("answer") if isinstance(result, dict) else None
                if not isinstance(reply_text, str) or not reply_text.strip():
                    continue

                cls._send_text_reply(recipient_user_id, reply_text.strip(), channel_config)
                try:
                    OmnichannelOpsService.record_message(
                        {
                            "tenant_id": app.tenant_id,
                            "channel_id": channel_id,
                            "external_user_id": recipient_user_id,
                            "direction": OmniChannelMessageDirection.OUTBOUND,
                            "source": OmniChannelMessageSource.SYSTEM,
                            "content": reply_text.strip(),
                            "external_message_id": event.get("message_id"),
                            "attachments": [],
                            "metadata": {},
                            "created_at": None,
                        }
                    )
                except Exception:
                    logger.debug("Failed to persist outbound Zalo message channel=%s", channel_id, exc_info=True)
                sent_count += 1
            except Exception:
                logger.exception(
                    "Failed processing Zalo event for channel=%s external_user_id=%s",
                    channel_id,
                    recipient_user_id,
                )
        return sent_count

