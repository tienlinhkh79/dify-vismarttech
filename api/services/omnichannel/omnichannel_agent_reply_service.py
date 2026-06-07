"""Console-initiated outbound messages (human agent) for supported omnichannel providers."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import (
    OmniChannelConversation,
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
    OmniChannelType,
)
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_graph_profile import fetch_page_profile
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService
from services.omnichannel.zalo_message_map_service import ZaloMessageMapService
from services.omnichannel.zalo_oa_consultation_service import ZaloOaConsultationService
from services.omnichannel.zalo_oa_profile import fetch_zalo_oa_display
from services.omnichannel.zalo_oauth_service import ZaloOAuthService
from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService
from services.omnichannel.zalo_runtime_service import ZaloRuntimeService

_AttachmentType = Literal["image", "video", "audio", "file"]


class OmnichannelAgentReplyService:
    """Send a manual reply from the console inbox and persist it as an outbound message."""

    @classmethod
    def send_reply(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
        text: str,
        attachment_url: str | None = None,
        attachment_type: _AttachmentType | None = None,
        quote_message_id: str | None = None,
    ) -> dict[str, Any]:
        body = (text or "").strip()
        url = (attachment_url or "").strip()
        if not body and not url:
            raise ValueError("Message text or attachment_url is required")
        if url and not attachment_type:
            raise ValueError("attachment_type is required when attachment_url is set")
        if url and not url.lower().startswith("https://"):
            raise ValueError("attachment_url must be an https URL")

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
            external_user_id = conv.external_user_id
            channel_type = conv.channel_type

        meta_actor: dict[str, str] = {}
        attachments: list[dict[str, Any]] = []
        zalo_msg_id = ""

        if channel_type in (OmniChannelType.FACEBOOK_MESSENGER, OmniChannelType.INSTAGRAM_DM):
            cfg = ChannelConfigService.get_meta_channel_config(channel_id)
            if not cfg or cfg["tenant_id"] != tenant_id:
                raise ValueError("Channel not found")
            token = (cfg.get("page_access_token") or "").strip()
            if not token:
                raise ValueError("Channel access token is missing; reconnect the channel in Settings → Inboxes")
            graph_ver = cfg.get("graph_api_version") or "v23.0"
            page_prof = fetch_page_profile(page_id=cfg["page_id"], access_token=token, graph_version=graph_ver)
            meta_actor["channel_actor_name"] = page_prof.get("name") or ""
            meta_actor["channel_actor_picture_url"] = page_prof.get("picture_url") or ""

            if url and attachment_type:
                MessengerRuntimeService._send_attachment_reply(
                    recipient_psid=external_user_id,
                    attachment_type=attachment_type,
                    attachment_url=url,
                    channel_config={
                        "app_id": cfg["app_id"],
                        "page_access_token": token,
                        "graph_api_version": graph_ver,
                    },
                )
                attachments.append({"type": attachment_type, "url": url})
            if body:
                MessengerRuntimeService._send_text_reply(
                    recipient_psid=external_user_id,
                    message_text=body,
                    channel_config={
                        "app_id": cfg["app_id"],
                        "page_access_token": token,
                        "graph_api_version": graph_ver,
                    },
                )
        elif channel_type == OmniChannelType.ZALO_OA:
            ZaloOAuthService.refresh_tokens_for_channel(channel_id, leeway_seconds=3600)
            cfg = ChannelConfigService.get_zalo_channel_config(channel_id)
            if not cfg or cfg["tenant_id"] != tenant_id:
                raise ValueError("Channel not found")
            ztoken = (cfg.get("oa_access_token") or "").strip()
            if not ztoken:
                raise ValueError("Zalo OA token is missing; complete OAuth under Settings → Inboxes")
            zprof = fetch_zalo_oa_display(access_token=ztoken)
            meta_actor["channel_actor_name"] = zprof.get("name") or ""
            meta_actor["channel_actor_picture_url"] = zprof.get("avatar_url") or ""
            quote_zalo_id = ""
            if quote_message_id:
                quote_zalo_id = ZaloMessageMapService.find_zalo_msg_id(
                    channel_id=channel_id,
                    omnichannel_message_id=quote_message_id,
                ) or ""
            ZaloOaConsultationService.on_outbound(
                tenant_id=tenant_id,
                channel_id=channel_id,
                user_id=external_user_id,
            )
            if url and attachment_type:
                zalo_msg_id = ZaloRuntimeService.send_attachment_reply(
                    external_user_id,
                    attachment_url=url,
                    attachment_type=attachment_type,
                    caption=body,
                    channel_config=cfg,
                )
                attachments.append({"type": attachment_type, "url": url})
            if body and not (url and attachment_type):
                zalo_msg_id = ZaloRuntimeService.send_text_reply(
                    external_user_id,
                    body,
                    channel_config=cfg,
                    quote_message_id=quote_zalo_id or None,
                )
            elif body and url and attachment_type:
                pass
        elif channel_type == OmniChannelType.TIKTOK_MESSAGING:
            cfg = ChannelConfigService.get_meta_channel_config(channel_id)
            if not cfg or cfg["tenant_id"] != tenant_id:
                raise ValueError("Channel not found")
            token = (cfg.get("page_access_token") or "").strip()
            if not token:
                raise ValueError("Channel access token is missing; reconnect the channel in Settings → Inboxes")
            graph_ver = cfg.get("graph_api_version") or "v23.0"
            page_prof = fetch_page_profile(page_id=cfg["page_id"], access_token=token, graph_version=graph_ver)
            meta_actor["channel_actor_name"] = page_prof.get("name") or ""
            meta_actor["channel_actor_picture_url"] = page_prof.get("picture_url") or ""
            if url and attachment_type:
                MessengerRuntimeService._send_attachment_reply(
                    recipient_psid=external_user_id,
                    attachment_type=attachment_type,
                    attachment_url=url,
                    channel_config={
                        "app_id": cfg["app_id"],
                        "page_access_token": token,
                        "graph_api_version": graph_ver,
                    },
                )
                attachments.append({"type": attachment_type, "url": url})
            if body:
                MessengerRuntimeService._send_text_reply(
                    recipient_psid=external_user_id,
                    message_text=body,
                    channel_config={
                        "app_id": cfg["app_id"],
                        "page_access_token": token,
                        "graph_api_version": graph_ver,
                    },
                )
        elif channel_type == OmniChannelType.ZALO_PERSONAL:
            ZaloPersonalSessionService.send_text_message(
                channel_id=channel_id,
                thread_id=external_user_id,
                text=body or (f"[attachment:{attachment_type}]" if url else ""),
            )
        else:
            raise ValueError("Unsupported channel type for manual replies")

        reply_meta: dict[str, object] = {"inbox_console": True}
        if quote_message_id:
            preview = ZaloMessageMapService.build_quote_preview(
                channel_id=channel_id,
                quote_zalo_msg_id=ZaloMessageMapService.find_zalo_msg_id(
                    channel_id=channel_id,
                    omnichannel_message_id=quote_message_id,
                )
                or "",
            )
            if preview:
                reply_meta["quote_preview"] = preview
            reply_meta["reply_to_message_id"] = quote_message_id

        record: MessageWritePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "external_user_id": external_user_id,
            "direction": OmniChannelMessageDirection.OUTBOUND,
            "source": OmniChannelMessageSource.AGENT,
            "content": body or (f"[attachment:{attachment_type}] {url}" if url else ""),
            "external_message_id": zalo_msg_id or None,
            "attachments": attachments,
            "metadata": reply_meta,
            "channel_actor_name": meta_actor.get("channel_actor_name") or None,
            "channel_actor_picture_url": meta_actor.get("channel_actor_picture_url") or None,
            "created_at": None,
        }
        saved = OmnichannelOpsService.record_message(record)
        if channel_type == OmniChannelType.ZALO_OA and zalo_msg_id:
            ZaloMessageMapService.record_if_new(
                channel_id=channel_id,
                zalo_msg_id=zalo_msg_id,
                omnichannel_message_id=str(saved.get("id") or ""),
                direction="out",
                zalo_thread_id=external_user_id,
            )
        return saved
