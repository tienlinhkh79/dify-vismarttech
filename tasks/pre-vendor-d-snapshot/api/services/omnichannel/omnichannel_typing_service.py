"""Send typing indicators from console agents to customers on supported channels."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelConversation, OmniChannelType
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.zalo_personal_presence_service import ZaloPersonalPresenceService

TypingAction = Literal["typing_on", "typing_off"]


class OmnichannelTypingService:
    @classmethod
    def send_typing(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
        action: TypingAction,
    ) -> dict[str, str]:
        with Session(db.engine, expire_on_commit=False) as session:
            conv = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conv:
                raise ValueError("Conversation not found")

        if conv.channel_type not in {
            OmniChannelType.FACEBOOK_MESSENGER,
            OmniChannelType.INSTAGRAM_DM,
            OmniChannelType.ZALO_PERSONAL,
        }:
            return {"status": "unsupported", "channel_type": conv.channel_type.value}

        if conv.channel_type == OmniChannelType.ZALO_PERSONAL:
            if action == "typing_on":
                ZaloPersonalPresenceService.send_typing(
                    channel_id=channel_id,
                    thread_id=conv.external_user_id,
                )
            return {"status": "sent", "action": action}

        cfg = ChannelConfigService.get_meta_channel_config(channel_id)
        if not cfg or cfg["tenant_id"] != tenant_id:
            raise ValueError("Channel not found")
        token = (cfg.get("page_access_token") or "").strip()
        if not token:
            raise ValueError("Channel access token is missing")

        channel_config = {
            "app_id": cfg["app_id"],
            "page_access_token": token,
            "graph_api_version": cfg.get("graph_api_version") or "v23.0",
        }
        MessengerRuntimeService._send_sender_action(
            recipient_psid=conv.external_user_id,
            action=action,
            channel_config=channel_config,
        )
        return {"status": "sent", "action": action}
