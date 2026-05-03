"""Runtime flow for Messenger <-> Dify bidirectional chat."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Literal, NotRequired, TypedDict, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.app.entities.app_invoke_entities import InvokeFrom
from core.helper.ssrf_proxy import ssrf_proxy
from extensions.ext_database import db
from extensions.ext_redis import redis_client
from models.model import App, AppMode
from services.app_generate_service import AppGenerateService
from services.end_user_service import EndUserService
from services.omnichannel.messenger_graph_profile import (
    extract_graph_picture_url,
    fetch_messenger_user_profile,
    fetch_page_profile,
)
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService
from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from models.trigger import OmniChannelMessageDirection, OmniChannelMessageSource

logger = logging.getLogger(__name__)


class MessengerRuntimeConfig(TypedDict):
    app_id: str
    page_access_token: str
    graph_api_version: str


class MessengerTextReply(TypedDict):
    type: Literal["text"]
    text: str


class MessengerAttachmentReply(TypedDict):
    type: Literal["attachment"]
    attachment_type: Literal["image", "video", "audio", "file"]
    url: str


class MessengerSenderActionReply(TypedDict):
    type: Literal["sender_action"]
    action: Literal["typing_on", "typing_off", "mark_seen"]


class MessengerQuickReplyItem(TypedDict):
    content_type: Literal["text"]
    title: str
    payload: str
    image_url: NotRequired[str]


class MessengerQuickRepliesReply(TypedDict):
    type: Literal["quick_replies"]
    text: str
    quick_replies: list[MessengerQuickReplyItem]


class MessengerTemplateReply(TypedDict):
    type: Literal["template"]
    template_payload: dict[str, Any]


MessengerReplyPayload = (
    MessengerTextReply
    | MessengerAttachmentReply
    | MessengerSenderActionReply
    | MessengerQuickRepliesReply
    | MessengerTemplateReply
)


class MessengerRuntimeService:
    _DEDUP_TTL_SECONDS = 300
    _MERGE_WINDOW_MS = 4000

    @staticmethod
    def _extract_markdown_image_urls(text: str) -> tuple[str, list[str]]:
        pattern = re.compile(r"!\[[^\]]*]\((https?://[^\s)]+)\)")
        image_urls = [match.group(1).strip() for match in pattern.finditer(text) if match.group(1).strip()]
        cleaned = pattern.sub("", text)
        # Normalize whitespace after removing markdown image syntax.
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned, image_urls

    @staticmethod
    def _normalize_llm_text_reply(text: str) -> str:
        value = text.strip()
        value = re.sub(r"^\s*text\s*:\s*", "", value, flags=re.IGNORECASE)
        if value.startswith("```") and value.endswith("```"):
            value = value[3:-3].strip()
        return value

    """Execute the inbound AI generation and outbound Messenger send flow."""

    @staticmethod
    def _build_event_query(event: OmniChannelIncomingEvent) -> str:
        text = str(event.get("text") or "").strip()
        attachments = event.get("attachments") or []
        if not attachments:
            return text

        attachment_lines = [
            f"- {item.get('type', 'attachment')}: {item.get('url', '')}"
            for item in attachments
            if str(item.get("url") or "").strip()
        ]
        if not attachment_lines:
            return text

        attachment_context = "User sent these Meta channel attachments:\n" + "\n".join(attachment_lines)
        if text:
            return f"{text}\n\n{attachment_context}"
        return f"{attachment_context}\n\nPlease analyze the attachment content and reply helpfully."

    @staticmethod
    def _build_event_files(event: OmniChannelIncomingEvent) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        for item in event.get("attachments") or []:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            files.append(
                {
                    "transfer_method": "remote_url",
                    "url": url,
                }
            )
        return files

    @classmethod
    def _merge_close_events(cls, events: list[OmniChannelIncomingEvent]) -> list[OmniChannelIncomingEvent]:
        if len(events) <= 1:
            return events

        merged: list[OmniChannelIncomingEvent] = []
        for event in events:
            raw_event = event.get("raw_event") or {}
            current_ts = int(raw_event.get("timestamp") or 0)
            if not merged:
                merged.append(event)
                continue

            prev = merged[-1]
            prev_raw = prev.get("raw_event") or {}
            prev_ts = int(prev_raw.get("timestamp") or 0)
            same_sender = prev.get("external_user_id") == event.get("external_user_id")
            close_enough = current_ts > 0 and prev_ts > 0 and (current_ts - prev_ts) <= cls._MERGE_WINDOW_MS

            if not same_sender or not close_enough:
                merged.append(event)
                continue

            prev_text = str(prev.get("text") or "").strip()
            curr_text = str(event.get("text") or "").strip()
            merged_text = "\n".join([part for part in [prev_text, curr_text] if part])
            prev["text"] = merged_text

            prev_attachments = list(prev.get("attachments") or [])
            curr_attachments = list(event.get("attachments") or [])
            if curr_attachments:
                prev["attachments"] = prev_attachments + curr_attachments

            if event.get("message_id"):
                prev["message_id"] = event["message_id"]
            prev["raw_event"] = event.get("raw_event", prev["raw_event"])

        return merged

    @staticmethod
    def _simulate_human_typing_delay(reply_text: str) -> None:
        # Keep delay short enough for UX, long enough to surface typing indicator.
        text_length = len(reply_text.strip())
        if text_length <= 0:
            delay_seconds = 0.8
        elif text_length <= 120:
            delay_seconds = 1.2
        else:
            delay_seconds = 1.8
        time.sleep(delay_seconds)

    @classmethod
    def _should_process_event(cls, channel_id: str, event: OmniChannelIncomingEvent) -> bool:
        message_id = str(event.get("message_id") or "").strip()
        if message_id:
            dedup_fingerprint = message_id
        else:
            raw_event = event.get("raw_event") or {}
            timestamp = str(raw_event.get("timestamp") or "")
            text = str(event.get("text") or "")
            external_user_id = str(event.get("external_user_id") or "")
            first_attachment_url = ""
            attachments = event.get("attachments") or []
            if attachments:
                first_attachment_url = str(attachments[0].get("url") or "")
            payload = f"{channel_id}|{external_user_id}|{timestamp}|{text}|{first_attachment_url}"
            dedup_fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        dedup_key = f"omnichannel:messenger:event:{channel_id}:{dedup_fingerprint}"
        try:
            inserted = redis_client.set(dedup_key, b"1", ex=cls._DEDUP_TTL_SECONDS, nx=True)
            return bool(inserted)
        except Exception:
            logger.debug("Redis dedup check failed, fallback to process event. key=%s", dedup_key, exc_info=True)
            return True

    @staticmethod
    def _get_reply_app(app_id: str) -> App:
        with Session(db.engine, expire_on_commit=False) as session:
            app = session.scalar(select(App).where(App.id == app_id))
        if not app:
            raise ValueError("Configured messenger app does not exist")

        app_mode = AppMode.value_of(app.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise ValueError("Configured Messenger app must be a chat-capable app")
        return app

    @staticmethod
    def _generate_reply(
        app: App,
        channel_id: str,
        event: OmniChannelIncomingEvent,
        *,
        record_message_result: dict[str, Any] | None = None,
    ) -> str | None:
        session_user_id = f"messenger:{channel_id}:{event['external_user_id']}"
        end_user = EndUserService.get_or_create_end_user_by_type(
            type=InvokeFrom.SERVICE_API,
            tenant_id=app.tenant_id,
            app_id=app.id,
            user_id=session_user_id,
        )

        event_query = MessengerRuntimeService._build_event_query(event)
        if not event_query:
            return None

        workflow_start_inputs: dict[str, str] = {}
        if record_message_result:
            workflow_start_inputs = {
                OmnichannelAppStartInputKey.CHANNEL_ID: channel_id,
                OmnichannelAppStartInputKey.CHANNEL_TYPE: str(record_message_result.get("channel_type") or ""),
                OmnichannelAppStartInputKey.CONVERSATION_ID: str(record_message_result.get("conversation_id") or ""),
                OmnichannelAppStartInputKey.EXTERNAL_USER_ID: str(event.get("external_user_id") or ""),
            }

        args: dict[str, Any] = {
            "inputs": workflow_start_inputs,
            "query": event_query,
            "files": MessengerRuntimeService._build_event_files(event),
            "response_mode": "blocking",
            "auto_generate_name": False,
        }
        result = AppGenerateService.generate(
            app_model=app,
            user=end_user,
            args=args,
            invoke_from=InvokeFrom.SERVICE_API,
            streaming=False,
        )

        if isinstance(result, dict):
            answer = result.get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer
        return None

    @staticmethod
    def _record_message(
        *,
        app: App,
        channel_id: str,
        event: OmniChannelIncomingEvent,
        direction: OmniChannelMessageDirection,
        content: str,
        source: OmniChannelMessageSource = OmniChannelMessageSource.WEBHOOK,
        participant_display_name: str | None = None,
        participant_profile_pic_url: str | None = None,
        channel_actor_name: str | None = None,
        channel_actor_picture_url: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            payload: dict[str, Any] = {
                "tenant_id": app.tenant_id,
                "channel_id": channel_id,
                "external_user_id": event["external_user_id"],
                "direction": direction,
                "source": source,
                "content": content,
                "external_message_id": event.get("message_id"),
                "attachments": list(event.get("attachments") or []),
                "metadata": {"raw_event": event.get("raw_event") or {}},
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
            return OmnichannelOpsService.record_message(cast(MessageWritePayload, payload))
        except Exception:
            logger.debug("Failed to persist omnichannel message channel=%s", channel_id, exc_info=True)
            return None

    @staticmethod
    def _send_quick_replies_reply(
        recipient_psid: str,
        message_text: str,
        quick_replies: list[MessengerQuickReplyItem],
        channel_config: MessengerRuntimeConfig,
    ) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/me/messages"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["page_access_token"]},
            json={
                "recipient": {"id": recipient_psid},
                "messaging_type": "RESPONSE",
                "message": {
                    "text": message_text,
                    "quick_replies": quick_replies,
                },
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _send_template_reply(
        recipient_psid: str,
        template_payload: dict[str, Any],
        channel_config: MessengerRuntimeConfig,
    ) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/me/messages"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["page_access_token"]},
            json={
                "recipient": {"id": recipient_psid},
                "messaging_type": "RESPONSE",
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": template_payload,
                    }
                },
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _send_text_reply(recipient_psid: str, message_text: str, channel_config: MessengerRuntimeConfig) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/me/messages"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["page_access_token"]},
            json={
                "recipient": {"id": recipient_psid},
                "messaging_type": "RESPONSE",
                "message": {"text": message_text},
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _send_attachment_reply(
        recipient_psid: str,
        attachment_type: Literal["image", "video", "audio", "file"],
        attachment_url: str,
        channel_config: MessengerRuntimeConfig,
    ) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/me/messages"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["page_access_token"]},
            json={
                "recipient": {"id": recipient_psid},
                "messaging_type": "RESPONSE",
                "message": {
                    "attachment": {
                        "type": attachment_type,
                        "payload": {"url": attachment_url, "is_reusable": True},
                    }
                },
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _send_sender_action(
        recipient_psid: str,
        action: Literal["typing_on", "typing_off", "mark_seen"],
        channel_config: MessengerRuntimeConfig,
    ) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/me/messages"
        response = ssrf_proxy.post(
            endpoint,
            params={"access_token": channel_config["page_access_token"]},
            json={
                "recipient": {"id": recipient_psid},
                "sender_action": action,
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _send_comment_reply(*, comment_id: str, message_text: str, channel_config: MessengerRuntimeConfig) -> None:
        endpoint = f"https://graph.facebook.com/{channel_config['graph_api_version']}/{comment_id}/comments"
        response = ssrf_proxy.post(
            endpoint,
            params={
                "access_token": channel_config["page_access_token"],
                "message": message_text,
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    @staticmethod
    def _parse_reply_payload(reply_text: str) -> MessengerReplyPayload:
        try:
            data = json.loads(reply_text)
        except json.JSONDecodeError:
            return {"type": "text", "text": reply_text}

        if not isinstance(data, dict):
            return {"type": "text", "text": reply_text}

        reply_type = data.get("type")
        if reply_type == "attachment":
            attachment_type = data.get("attachment_type")
            attachment_url = data.get("url")
            if (
                isinstance(attachment_type, str)
                and attachment_type in {"image", "video", "audio", "file"}
                and isinstance(attachment_url, str)
                and attachment_url.strip()
            ):
                return {
                    "type": "attachment",
                    "attachment_type": attachment_type,
                    "url": attachment_url.strip(),
                }
        elif reply_type == "quick_replies":
            text = data.get("text")
            quick_replies = data.get("quick_replies")
            if isinstance(text, str) and text.strip() and isinstance(quick_replies, list):
                normalized_quick_replies: list[MessengerQuickReplyItem] = []
                for item in quick_replies:
                    if not isinstance(item, dict):
                        continue
                    content_type = item.get("content_type", "text")
                    title = item.get("title")
                    payload = item.get("payload")
                    image_url = item.get("image_url")
                    if (
                        content_type == "text"
                        and isinstance(title, str)
                        and title.strip()
                        and isinstance(payload, str)
                        and payload.strip()
                    ):
                        normalized_item: MessengerQuickReplyItem = {
                            "content_type": "text",
                            "title": title.strip(),
                            "payload": payload.strip(),
                        }
                        if isinstance(image_url, str) and image_url.strip():
                            normalized_item["image_url"] = image_url.strip()
                        normalized_quick_replies.append(normalized_item)
                if normalized_quick_replies:
                    return {
                        "type": "quick_replies",
                        "text": text.strip(),
                        "quick_replies": normalized_quick_replies,
                    }
        elif reply_type == "template":
            template_payload = data.get("template_payload")
            if isinstance(template_payload, dict) and template_payload:
                return {
                    "type": "template",
                    "template_payload": template_payload,
                }
        elif reply_type == "sender_action":
            action = data.get("action")
            if isinstance(action, str) and action in {"typing_on", "typing_off", "mark_seen"}:
                return {"type": "sender_action", "action": action}
        elif reply_type == "text":
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                return {"type": "text", "text": MessengerRuntimeService._normalize_llm_text_reply(text)}

        return {"type": "text", "text": reply_text}

    @classmethod
    def _to_plain_text_reply(cls, reply_text: str) -> str:
        payload = cls._parse_reply_payload(reply_text)
        if payload["type"] == "text":
            return cls._normalize_llm_text_reply(payload["text"])
        if payload["type"] == "quick_replies":
            return cls._normalize_llm_text_reply(payload["text"])
        if payload["type"] == "template":
            return json.dumps(payload["template_payload"], ensure_ascii=False)
        if payload["type"] == "attachment":
            return payload["url"].strip()
        return ""

    @classmethod
    def _send_reply(cls, recipient_psid: str, reply_text: str, channel_config: MessengerRuntimeConfig) -> bool:
        payload = cls._parse_reply_payload(reply_text)
        if payload["type"] == "attachment":
            cls._send_attachment_reply(
                recipient_psid=recipient_psid,
                attachment_type=payload["attachment_type"],
                attachment_url=payload["url"],
                channel_config=channel_config,
            )
            return True
        if payload["type"] == "sender_action":
            cls._send_sender_action(
                recipient_psid=recipient_psid,
                action=payload["action"],
                channel_config=channel_config,
            )
            return False
        if payload["type"] == "quick_replies":
            cls._send_quick_replies_reply(
                recipient_psid=recipient_psid,
                message_text=payload["text"],
                quick_replies=payload["quick_replies"],
                channel_config=channel_config,
            )
            return True
        if payload["type"] == "template":
            cls._send_template_reply(
                recipient_psid=recipient_psid,
                template_payload=payload["template_payload"],
                channel_config=channel_config,
            )
            return True

        normalized_text = cls._normalize_llm_text_reply(payload["text"])
        text_to_send, image_urls = cls._extract_markdown_image_urls(normalized_text)
        sent = False
        if text_to_send:
            cls._send_text_reply(recipient_psid, text_to_send, channel_config)
            sent = True
        for image_url in image_urls:
            cls._send_attachment_reply(recipient_psid, "image", image_url, channel_config)
            sent = True
        return sent

    @classmethod
    def process_events(
        cls, channel_id: str, events: list[OmniChannelIncomingEvent], channel_config: MessengerRuntimeConfig
    ) -> int:
        """Generate and send replies for all normalized inbound Messenger events."""
        if not events:
            return 0
        events = cls._merge_close_events(events)

        app = cls._get_reply_app(channel_config["app_id"])
        sent_count = 0
        page_profile = {"name": "", "picture_url": ""}
        if events:
            page_id = str(events[0].get("external_account_id") or "").strip()
            if page_id:
                page_profile = fetch_page_profile(
                    page_id=page_id,
                    access_token=channel_config["page_access_token"],
                    graph_version=channel_config["graph_api_version"],
                )
        user_profile_cache: dict[str, tuple[str, str]] = {}

        def user_profile_for(psid: str) -> tuple[str, str]:
            if psid in user_profile_cache:
                return user_profile_cache[psid]
            prof = fetch_messenger_user_profile(
                psid=psid,
                access_token=channel_config["page_access_token"],
                graph_version=channel_config["graph_api_version"],
            )
            user_profile_cache[psid] = (str(prof.get("name") or ""), str(prof.get("profile_pic") or ""))
            return user_profile_cache[psid]

        def sender_display_for_event(ev: OmniChannelIncomingEvent, psid: str) -> tuple[str, str]:
            """Prefer Page-feed comment webhook `from` (name/picture); else Graph User Profile for PSID."""
            wname, wpic = "", ""
            if str(ev.get("interaction_type") or "") == "facebook_comment":
                raw = ev.get("raw_event") or {}
                if isinstance(raw, dict):
                    from_obj = raw.get("from")
                    if isinstance(from_obj, dict):
                        wname = str(from_obj.get("name") or "").strip()
                        wpic = str(from_obj.get("profile_pic") or "").strip()
                        if not wpic:
                            wpic = extract_graph_picture_url(from_obj.get("picture"))
            gname, gpic = user_profile_for(psid)
            return (wname or gname), (wpic or gpic)

        for event in events:
            recipient_psid = event["external_user_id"]
            interaction_type = str(event.get("interaction_type") or "messenger_message")
            is_comment_event = interaction_type == "facebook_comment"
            try:
                if not cls._should_process_event(channel_id, event):
                    logger.info(
                        "Skip duplicated Messenger event channel=%s external_user_id=%s message_id=%s",
                        channel_id,
                        recipient_psid,
                        event.get("message_id"),
                    )
                    continue
                if not is_comment_event:
                    cls._send_sender_action(
                        recipient_psid=recipient_psid,
                        action="mark_seen",
                        channel_config=channel_config,
                    )
                    cls._send_sender_action(
                        recipient_psid=recipient_psid,
                        action="typing_on",
                        channel_config=channel_config,
                    )
                uname, upic = sender_display_for_event(event, recipient_psid)
                record_message_result = cls._record_message(
                    app=app,
                    channel_id=channel_id,
                    event=event,
                    direction=OmniChannelMessageDirection.INBOUND,
                    source=OmniChannelMessageSource.WEBHOOK,
                    content=str(event.get("text") or "").strip(),
                    participant_display_name=uname or None,
                    participant_profile_pic_url=upic or None,
                )
                reply_text = cls._generate_reply(
                    app, channel_id, event, record_message_result=record_message_result
                )
                if not reply_text:
                    continue
                if is_comment_event:
                    comment_id = str(event.get("reply_target_id") or event.get("message_id") or "").strip()
                    if not comment_id:
                        logger.info(
                            "Skip comment reply due to missing comment target channel=%s external_user_id=%s",
                            channel_id,
                            recipient_psid,
                        )
                        continue
                    plain_text_reply = cls._to_plain_text_reply(reply_text)
                    if not plain_text_reply:
                        logger.info(
                            "Skip empty comment reply channel=%s external_user_id=%s",
                            channel_id,
                            recipient_psid,
                        )
                        continue
                    cls._send_comment_reply(
                        comment_id=comment_id,
                        message_text=plain_text_reply,
                        channel_config=channel_config,
                    )
                    is_message_sent = True
                else:
                    cls._simulate_human_typing_delay(reply_text)
                    is_message_sent = cls._send_reply(recipient_psid, reply_text, channel_config)
                if is_message_sent:
                    cls._record_message(
                        app=app,
                        channel_id=channel_id,
                        event=event,
                        direction=OmniChannelMessageDirection.OUTBOUND,
                        source=OmniChannelMessageSource.SYSTEM,
                        content=reply_text.strip(),
                        channel_actor_name=str(page_profile.get("name") or "").strip() or None,
                        channel_actor_picture_url=str(page_profile.get("picture_url") or "").strip() or None,
                    )
                    sent_count += 1
            except Exception:
                logger.exception(
                    "Failed processing Messenger event for channel=%s external_user_id=%s",
                    channel_id,
                    recipient_psid,
                )
            finally:
                if not is_comment_event:
                    try:
                        cls._send_sender_action(
                            recipient_psid=recipient_psid,
                            action="typing_off",
                            channel_config=channel_config,
                        )
                    except Exception:
                        logger.debug("Failed sending typing_off for channel=%s external_user_id=%s", channel_id, recipient_psid)
        return sent_count

