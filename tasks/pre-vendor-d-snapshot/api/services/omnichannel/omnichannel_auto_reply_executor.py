"""Execute a single debounced omnichannel auto-reply after fragments are merged."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from models.trigger import OmniChannelType
from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.omnichannel_auto_reply_debounce_service import (
    AutoReplyDebounceFragment,
    OmnichannelAutoReplyDebounceService,
)

logger = logging.getLogger(__name__)


class OmnichannelAutoReplyExecutor:
    @classmethod
    def execute_merged(
        cls,
        *,
        channel_id: str,
        external_user_id: str,
        fragments: list[AutoReplyDebounceFragment],
    ) -> None:
        if not fragments:
            return

        last = fragments[-1]
        channel_type = str(last.get("channel_type") or "").strip()
        tenant_id = str(last.get("tenant_id") or "").strip()
        merged_query = OmnichannelAutoReplyDebounceService.merge_texts(fragments)
        if not merged_query:
            merged_query = str((last.get("event") or {}).get("text") or "").strip()
        if not merged_query:
            return

        merged_event = cls._merge_events(fragments)
        conversation_id = str(last.get("conversation_id") or "").strip()
        if not conversation_id:
            for fragment in reversed(fragments):
                conversation_id = str(fragment.get("conversation_id") or "").strip()
                if conversation_id:
                    break

        if channel_type == OmniChannelType.ZALO_OA.value:
            from services.omnichannel.zalo_runtime_service import ZaloRuntimeService

            ZaloRuntimeService.execute_auto_reply(
                channel_id=channel_id,
                event=merged_event,  # type: ignore[arg-type]
                channel_config_extras=last.get("extras") or {},
                conversation_id=conversation_id,
                merged_query=merged_query,
            )
            return

        if channel_type == OmniChannelType.ZALO_PERSONAL.value:
            from services.omnichannel.zalo_personal_runtime_service import ZaloPersonalRuntimeService

            ZaloPersonalRuntimeService.execute_auto_reply(
                channel_id=channel_id,
                tenant_id=tenant_id,
                thread_id=external_user_id,
                record={"conversation_id": conversation_id, **(last.get("extras") or {})},
                event=merged_event,
                merged_query=merged_query,
            )
            return

        if channel_type in {OmniChannelType.FACEBOOK_MESSENGER.value, "facebook_messenger"}:
            from services.omnichannel.messenger_runtime_service import MessengerRuntimeService

            MessengerRuntimeService.execute_debounced_auto_reply(
                channel_id=channel_id,
                external_user_id=external_user_id,
                event=merged_event,
                conversation_id=conversation_id,
                merged_query=merged_query,
                extras=last.get("extras") or {},
            )
            return

        logger.warning(
            "Unsupported debounced auto-reply channel_type=%s channel=%s user=%s",
            channel_type,
            channel_id,
            external_user_id,
        )

    @classmethod
    def _merge_events(cls, fragments: list[AutoReplyDebounceFragment]) -> OmniChannelIncomingEvent:
        base = deepcopy(fragments[-1].get("event") or {})
        if not isinstance(base, dict):
            base = {}

        merged_text = OmnichannelAutoReplyDebounceService.merge_texts(fragments)
        if merged_text:
            base["text"] = merged_text

        all_attachments: list[dict[str, Any]] = []
        for fragment in fragments:
            event = fragment.get("event") or {}
            if not isinstance(event, dict):
                continue
            for item in event.get("attachments") or []:
                if isinstance(item, dict):
                    all_attachments.append(item)
        if all_attachments:
            base["attachments"] = all_attachments

        last_event = fragments[-1].get("event") or {}
        if isinstance(last_event, dict):
            if last_event.get("message_id"):
                base["message_id"] = last_event["message_id"]
            if last_event.get("raw_event"):
                base["raw_event"] = last_event["raw_event"]

        return base  # type: ignore[return-value]
