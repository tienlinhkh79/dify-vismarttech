"""Runtime flow for Zalo OA <-> Dify omnichannel (zca-bridge inbox-first pattern)."""

from __future__ import annotations

import logging
from typing import Any

from core.app.entities.app_invoke_entities import InvokeFrom
from models.trigger import OmniChannelMessageDirection, OmniChannelMessageSource, OmniChannelType
from services.app_generate_service import AppGenerateService
from services.end_user_service import EndUserService
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.omnichannel_auto_reply_debounce_service import OmnichannelAutoReplyDebounceService
from services.omnichannel.omnichannel_auto_reply_policy import OmnichannelAutoReplyPolicyService
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService
from services.omnichannel.omnichannel_reply_sender import OmnichannelReplySenderService
from services.omnichannel.omnichannel_workflow_inputs import build_workflow_start_inputs
from services.omnichannel.zalo_media_archive_service import ZaloMediaArchiveService
from services.omnichannel.zalo_message_map_service import ZaloMessageMapService
from services.omnichannel.zalo_oa_classify import ZaloOaWebhookEvent, format_self_outbound_content
from services.omnichannel.zalo_oa_consultation_service import ZaloOaConsultationService
from services.omnichannel.zalo_oa_info_card_service import ZaloOaInfoCardService
from services.omnichannel.zalo_oa_profile import fetch_zalo_oa_display, fetch_zalo_user_display
from services.omnichannel.zalo_oa_sender import OaWindowError, ZaloOaSender

logger = logging.getLogger(__name__)


class ZaloRuntimeService:
    """Persist Zalo OA messages to the inbox first, then optionally run the linked AI app."""

    @classmethod
    def process_events(
        cls,
        channel_id: str,
        events: list[OmniChannelIncomingEvent],
        channel_config: dict[str, Any],
    ) -> int:
        if not events:
            return 0

        tenant_id = str(channel_config.get("tenant_id") or "")
        access_token = str(channel_config.get("oa_access_token") or "").strip()
        dify_app_id = str(channel_config.get("app_id") or "").strip()
        sender = ZaloOaSender(access_token) if access_token else None

        processed = 0
        for raw_event in events:
            event: ZaloOaWebhookEvent = raw_event  # type: ignore[assignment]
            try:
                if event.get("is_self"):
                    if cls._process_self_event(
                        tenant_id=tenant_id,
                        channel_id=channel_id,
                        event=event,
                        access_token=access_token,
                    ):
                        processed += 1
                    continue

                record = cls._persist_inbound(
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    event=event,
                    access_token=access_token,
                    channel_config=channel_config,
                )
                if not record:
                    continue
                processed += 1

                if not dify_app_id or not sender:
                    continue
                from services.omnichannel.omnichannel_auto_reply_policy import OmnichannelAutoReplyPolicyService

                policy = OmnichannelAutoReplyPolicyService.load_for_channel(channel_id)
                if not policy or not OmnichannelAutoReplyPolicyService.should_auto_reply(
                    policy=policy,
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    external_user_id=str(event.get("external_user_id") or ""),
                ):
                    continue
                cls._maybe_auto_reply(
                    channel_id=channel_id,
                    event=event,
                    channel_config=channel_config,
                    record=record,
                    sender=sender,
                    dify_app_id=dify_app_id,
                )
            except Exception:
                logger.exception(
                    "Failed processing Zalo event channel=%s external_user_id=%s",
                    channel_id,
                    event.get("external_user_id"),
                )
        return processed

    @classmethod
    def _process_self_event(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        event: ZaloOaWebhookEvent,
        access_token: str,
    ) -> bool:
        """Import operator messages sent directly from the native Zalo app."""
        zalo_msg_id = str(event.get("message_id") or "").strip()
        if zalo_msg_id and ZaloMessageMapService.find_omnichannel_message_id(
            channel_id=channel_id, zalo_msg_id=zalo_msg_id
        ):
            return False

        content = format_self_outbound_content(str(event.get("text") or ""))
        oa_prof = fetch_zalo_oa_display(access_token=access_token)
        record = cls._write_message(
            tenant_id=tenant_id,
            channel_id=channel_id,
            event=event,
            direction=OmniChannelMessageDirection.OUTBOUND,
            source=OmniChannelMessageSource.WEBHOOK,
            content=content,
            channel_actor_name=oa_prof.get("name") or "",
            channel_actor_picture_url=oa_prof.get("avatar_url") or "",
        )
        if record and zalo_msg_id:
            ZaloMessageMapService.record_if_new(
                channel_id=channel_id,
                zalo_msg_id=zalo_msg_id,
                omnichannel_message_id=str(record.get("id") or ""),
                direction="out",
                zalo_thread_id=event["external_user_id"],
            )
        return bool(record)

    @classmethod
    def _persist_inbound(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        event: ZaloOaWebhookEvent,
        access_token: str,
        channel_config: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not MessengerRuntimeService._should_process_event(channel_id, event):
            return None

        cls._archive_event_media(channel_id=channel_id, event=event)
        user_prof = fetch_zalo_user_display(access_token=access_token, user_id=event["external_user_id"])
        record = cls._write_message(
            tenant_id=tenant_id,
            channel_id=channel_id,
            event=event,
            direction=OmniChannelMessageDirection.INBOUND,
            source=OmniChannelMessageSource.WEBHOOK,
            content=str(event.get("text") or "").strip(),
            participant_display_name=user_prof.get("name") or "",
            participant_profile_pic_url=user_prof.get("avatar_url") or "",
        )
        zalo_msg_id = str(event.get("message_id") or "").strip()
        if record and zalo_msg_id:
            ZaloMessageMapService.record_if_new(
                channel_id=channel_id,
                zalo_msg_id=zalo_msg_id,
                omnichannel_message_id=str(record.get("id") or ""),
                direction="in",
                zalo_thread_id=event["external_user_id"],
                quote_zalo_msg_id=str(event.get("quote_message_id") or "") or None,
            )
        user_id = event["external_user_id"]
        ZaloOaConsultationService.on_inbound(channel_id=channel_id, user_id=user_id)
        ZaloOaInfoCardService.maybe_send_on_first_inbound(
            channel_id=channel_id,
            user_id=user_id,
            channel_config=channel_config,
        )
        return record

    @classmethod
    def _maybe_auto_reply(
        cls,
        *,
        channel_id: str,
        event: ZaloOaWebhookEvent,
        channel_config: dict[str, Any],
        record: dict[str, Any],
        sender: ZaloOaSender,
        dify_app_id: str,
    ) -> None:
        event_query = MessengerRuntimeService._build_event_query(event)
        if not event_query:
            return

        tenant_id = str(channel_config.get("tenant_id") or "")
        external_user_id = str(event.get("external_user_id") or "")
        enqueued = OmnichannelAutoReplyDebounceService.enqueue(
            channel_type=OmniChannelType.ZALO_OA.value,
            channel_id=channel_id,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            fragment={
                "text": event_query,
                "conversation_id": str(record.get("conversation_id") or ""),
                "event": dict(event),
                "extras": {"dify_app_id": dify_app_id},
            },
        )
        if not enqueued:
            cls.execute_auto_reply(
                channel_id=channel_id,
                event=event,
                channel_config=channel_config,
                sender=sender,
                dify_app_id=dify_app_id,
                conversation_id=str(record.get("conversation_id") or ""),
                merged_query=event_query,
            )

    @classmethod
    def execute_auto_reply(
        cls,
        *,
        channel_id: str,
        event: ZaloOaWebhookEvent,
        channel_config: dict[str, Any] | None = None,
        sender: ZaloOaSender | None = None,
        dify_app_id: str | None = None,
        conversation_id: str = "",
        merged_query: str | None = None,
        channel_config_extras: dict[str, Any] | None = None,
    ) -> None:
        if channel_config is None:
            channel_config = ChannelConfigService.get_zalo_channel_config(channel_id, skip_oauth_refresh=False)
        if not channel_config:
            return

        tenant_id = str(channel_config.get("tenant_id") or "")
        external_user_id = str(event.get("external_user_id") or "")
        policy = OmnichannelAutoReplyPolicyService.load_for_channel(channel_id)
        if not policy or not OmnichannelAutoReplyPolicyService.should_auto_reply(
            policy=policy,
            tenant_id=tenant_id,
            channel_id=channel_id,
            external_user_id=external_user_id,
        ):
            return

        app_id = dify_app_id or str((channel_config_extras or {}).get("dify_app_id") or channel_config.get("app_id") or "").strip()
        if not app_id:
            return

        access_token = str(channel_config.get("oa_access_token") or "").strip()
        active_sender = sender or (ZaloOaSender(access_token) if access_token else None)
        if active_sender is None:
            return

        app = MessengerRuntimeService._get_reply_app(app_id)
        session_user_id = f"zalo:{channel_id}:{event['external_user_id']}"
        end_user = EndUserService.get_or_create_end_user_by_type(
            type=InvokeFrom.SERVICE_API,
            tenant_id=app.tenant_id,
            app_id=app.id,
            user_id=session_user_id,
        )
        event_query = (merged_query or "").strip() or MessengerRuntimeService._build_event_query(event)
        if not event_query:
            return

        workflow_start_inputs = build_workflow_start_inputs(
            channel_id=channel_id,
            channel_type=str(channel_config.get("channel_type") or OmniChannelType.ZALO_OA.value),
            conversation_id=conversation_id,
            external_user_id=external_user_id,
            event=event,
        )
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
            return

        user_id = event["external_user_id"]
        ZaloOaConsultationService.on_outbound(
            tenant_id=tenant_id,
            channel_id=channel_id,
            user_id=user_id,
        )
        try:
            send_result = OmnichannelReplySenderService.send(
                channel_type=OmniChannelType.ZALO_OA.value,
                recipient_id=user_id,
                reply_text=reply_text.strip(),
                channel_config=channel_config,
                quote_message_id=str(event.get("quote_message_id") or "") or None,
            )
        except OaWindowError as e:
            raise ValueError(str(e)) from e
        if not send_result["sent"]:
            return
        zalo_msg_id = send_result["external_message_ids"][0] if send_result["external_message_ids"] else ""
        oa_prof = fetch_zalo_oa_display(access_token=str(channel_config.get("oa_access_token") or ""))
        outbound_event: ZaloOaWebhookEvent = {
            **event,
            "message_id": zalo_msg_id or event.get("message_id"),
        }
        outbound = cls._write_message(
            tenant_id=tenant_id,
            channel_id=channel_id,
            event=outbound_event,
            direction=OmniChannelMessageDirection.OUTBOUND,
            source=OmniChannelMessageSource.SYSTEM,
            content=send_result["inbox_content"] or reply_text.strip(),
            channel_actor_name=oa_prof.get("name") or "",
            channel_actor_picture_url=oa_prof.get("avatar_url") or "",
        )
        if outbound and zalo_msg_id:
            ZaloMessageMapService.record_if_new(
                channel_id=channel_id,
                zalo_msg_id=zalo_msg_id,
                omnichannel_message_id=str(outbound.get("id") or ""),
                direction="out",
                zalo_thread_id=event["external_user_id"],
            )

    @staticmethod
    def _archive_event_media(*, channel_id: str, event: ZaloOaWebhookEvent) -> None:
        attachments = list(event.get("attachments") or [])
        if not attachments:
            return
        thread_id = event["external_user_id"]
        msg_id = str(event.get("message_id") or "unknown")
        archived: list[dict[str, str]] = []
        for item in attachments:
            href = str(item.get("url") or "").strip()
            if not href:
                continue
            archived_url = ZaloMediaArchiveService.download_and_archive(
                channel_id=channel_id,
                thread_id=thread_id,
                msg_id=msg_id,
                href=href,
                filename=href.rsplit("/", 1)[-1].split("?")[0] or "file",
                media_type=str(item.get("type") or "file"),
            )
            archived.append(
                {
                    "type": str(item.get("type") or "file"),
                    "url": archived_url or href,
                }
            )
        if archived:
            event["attachments"] = archived

    @classmethod
    def send_text_reply(
        cls,
        recipient_user_id: str,
        message_text: str,
        channel_config: dict[str, Any],
        *,
        quote_message_id: str | None = None,
    ) -> str:
        token = str(channel_config.get("oa_access_token") or "").strip()
        if not token:
            raise ValueError("Zalo OA access token is missing")
        try:
            return ZaloOaSender(token).send_text(
                recipient_user_id,
                message_text,
                quote_message_id=quote_message_id,
            )
        except OaWindowError as e:
            raise ValueError(str(e)) from e

    @classmethod
    def send_attachment_reply(
        cls,
        recipient_user_id: str,
        *,
        attachment_url: str,
        attachment_type: str,
        caption: str,
        channel_config: dict[str, Any],
    ) -> str:
        token = str(channel_config.get("oa_access_token") or "").strip()
        if not token:
            raise ValueError("Zalo OA access token is missing")
        try:
            return ZaloOaSender(token).send_attachment_from_url(
                recipient_user_id,
                attachment_url=attachment_url,
                attachment_type=attachment_type,
                caption=caption,
            )
        except OaWindowError as e:
            raise ValueError(str(e)) from e

    @staticmethod
    def _write_message(
        *,
        tenant_id: str,
        channel_id: str,
        event: ZaloOaWebhookEvent,
        direction: OmniChannelMessageDirection,
        source: OmniChannelMessageSource,
        content: str,
        participant_display_name: str = "",
        participant_profile_pic_url: str = "",
        channel_actor_name: str = "",
        channel_actor_picture_url: str = "",
    ) -> dict[str, Any] | None:
        metadata: dict[str, Any] = {
            "raw_event": event.get("raw_event") or {},
            "event_name": event.get("event_name") or "",
        }
        quote_zalo_id = str(event.get("quote_message_id") or "").strip()
        if quote_zalo_id:
            metadata["quote_zalo_msg_id"] = quote_zalo_id
            preview = ZaloMessageMapService.build_quote_preview(
                channel_id=channel_id,
                quote_zalo_msg_id=quote_zalo_id,
            )
            if preview:
                metadata["quote_preview"] = preview

        payload: MessageWritePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "external_user_id": event["external_user_id"],
            "direction": direction,
            "source": source,
            "content": content,
            "external_message_id": str(event.get("message_id") or "") or None,
            "attachments": list(event.get("attachments") or []),
            "metadata": metadata,
            "created_at": None,
        }
        if participant_display_name:
            payload["participant_display_name"] = participant_display_name
        if participant_profile_pic_url:
            payload["participant_profile_pic_url"] = participant_profile_pic_url
        if channel_actor_name:
            payload["channel_actor_name"] = channel_actor_name
        if channel_actor_picture_url:
            payload["channel_actor_picture_url"] = channel_actor_picture_url
        try:
            return OmnichannelOpsService.record_message(payload)
        except Exception:
            logger.debug("Failed to persist Zalo message channel=%s", channel_id, exc_info=True)
            return None
