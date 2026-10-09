"""Dispatch parsed omnichannel replies to provider-specific send APIs."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from services.omnichannel.omnichannel_reply_payload import (
    OmnichannelButton,
    OmnichannelCard,
    OmnichannelCardsReply,
    OmnichannelReplyPayload,
    OmnichannelReplyPayloadService,
    zalo_button_limit,
    zalo_card_limit,
)
from services.omnichannel.zalo_oa_sender import OaWindowError, ZaloOaSender
from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService

logger = logging.getLogger(__name__)


class OmnichannelReplySendResult(TypedDict):
    sent: bool
    external_message_ids: list[str]
    inbox_content: str


class ZaloOaReplyAdapter:
    @staticmethod
    def _resolve_card_url(card: OmnichannelCard) -> str:
        default_url = card.get("default_url")
        if isinstance(default_url, str) and default_url.strip():
            return default_url.strip()
        buttons = card.get("buttons") or []
        for button in buttons:
            if button["action"] == "url":
                url = button.get("url")
                if isinstance(url, str) and url.strip():
                    return url.strip()
        return ""

    @staticmethod
    def _to_zalo_button(button: OmnichannelButton) -> dict[str, object] | None:
        if button["action"] == "url":
            url = button.get("url")
            if not isinstance(url, str) or not url.strip():
                return None
            return {
                "title": button["title"],
                "type": "oa.open.url",
                "payload": {"url": url.strip()},
            }
        payload = button.get("payload")
        if not isinstance(payload, str) or not payload.strip():
            return None
        return {
            "title": button["title"],
            "type": "oa.query.show",
            "payload": payload.strip(),
        }

    @classmethod
    def _to_zalo_elements(cls, cards: list[OmnichannelCard]) -> list[dict[str, object]]:
        elements: list[dict[str, object]] = []
        for card in cards[:zalo_card_limit()]:
            element: dict[str, object] = {"title": card["title"]}
            subtitle = card.get("subtitle")
            if isinstance(subtitle, str) and subtitle.strip():
                element["subtitle"] = subtitle.strip()
            image_url = card.get("image_url")
            if isinstance(image_url, str) and image_url.strip():
                element["image_url"] = image_url.strip()
            card_url = cls._resolve_card_url(card)
            if card_url:
                element["default_action"] = {"type": "oa.open.url", "url": card_url}
            elements.append(element)
        return elements

    @classmethod
    def send(
        cls,
        *,
        sender: ZaloOaSender,
        recipient_id: str,
        payload: OmnichannelReplyPayload,
        quote_message_id: str | None = None,
    ) -> OmnichannelReplySendResult:
        message_ids: list[str] = []
        sent = False

        try:
            if payload["type"] == "text":
                text, image_urls = OmnichannelReplyPayloadService.extract_markdown_image_urls(payload["text"])
                plain = OmnichannelReplyPayloadService.strip_markdown_for_messaging(text)
                if plain:
                    message_ids.append(
                        sender.send_text(recipient_id, plain, quote_message_id=quote_message_id)
                    )
                    sent = True
                for image_url in image_urls:
                    message_ids.append(
                        sender.send_attachment_from_url(
                            recipient_id,
                            attachment_url=image_url,
                            attachment_type="image",
                        )
                    )
                    sent = True
            elif payload["type"] == "attachment":
                message_ids.append(
                    sender.send_attachment_from_url(
                        recipient_id,
                        attachment_url=payload["url"],
                        attachment_type=payload["attachment_type"],
                    )
                )
                sent = True
            elif payload["type"] == "cards":
                intro = payload.get("text")
                elements = cls._to_zalo_elements(payload["cards"])
                buttons = [
                    mapped
                    for raw in (payload.get("buttons") or [])[:zalo_button_limit()]
                    if (mapped := cls._to_zalo_button(raw))
                ]
                if elements:
                    message_ids.append(
                        sender.send_list_template(
                            recipient_id,
                            text=str(intro or "").strip(),
                            elements=elements,
                            buttons=buttons or None,
                            quote_message_id=quote_message_id,
                        )
                    )
                    sent = True
                elif isinstance(intro, str) and intro.strip():
                    message_ids.append(
                        sender.send_text(recipient_id, intro.strip(), quote_message_id=quote_message_id)
                    )
                    sent = True
            elif payload["type"] in {"actions", "quick_replies"}:
                if payload["type"] == "actions":
                    text = payload["text"]
                    raw_buttons = payload["buttons"]
                else:
                    text = payload["text"]
                    raw_buttons = [
                        {
                            "title": item["title"],
                            "action": "postback",
                            "payload": item["payload"],
                            **({"image_url": item["image_url"]} if item.get("image_url") else {}),
                        }
                        for item in payload["quick_replies"]
                    ]
                buttons = [
                    mapped
                    for raw in raw_buttons[:zalo_button_limit()]
                    if (mapped := cls._to_zalo_button(raw))
                ]
                if buttons:
                    elements: list[dict[str, object]] = []
                    if not text.strip():
                        text = "Chọn một tùy chọn:"
                    elements.append({"title": text.strip(), "subtitle": ""})
                    message_ids.append(
                        sender.send_list_template(
                            recipient_id,
                            text="",
                            elements=elements,
                            buttons=buttons,
                            quote_message_id=quote_message_id,
                        )
                    )
                    sent = True
                elif text.strip():
                    message_ids.append(
                        sender.send_text(recipient_id, text.strip(), quote_message_id=quote_message_id)
                    )
                    sent = True
            elif payload["type"] == "template":
                template_type = str(payload["template_payload"].get("template_type") or "")
                if template_type == "list":
                    message_ids.append(
                        sender.send_list_template(
                            recipient_id,
                            text="",
                            elements=list(payload["template_payload"].get("elements") or []),
                            buttons=list(payload["template_payload"].get("buttons") or []) or None,
                            quote_message_id=quote_message_id,
                        )
                    )
                    sent = True
                else:
                    message_ids.append(
                        sender.send_raw_template(
                            recipient_id,
                            template_payload=payload["template_payload"],
                            quote_message_id=quote_message_id,
                        )
                    )
                    sent = True
        except OaWindowError:
            raise

        return {
            "sent": sent,
            "external_message_ids": [msg_id for msg_id in message_ids if msg_id],
            "inbox_content": OmnichannelReplyPayloadService.to_inbox_content(payload),
        }


class MessengerReplyAdapter:
    @staticmethod
    def _to_messenger_card_button(button: OmnichannelButton) -> dict[str, str] | None:
        if button["action"] == "url":
            url = button.get("url")
            if not isinstance(url, str) or not url.strip():
                return None
            return {"type": "web_url", "url": url.strip(), "title": button["title"]}
        payload = button.get("payload")
        if not isinstance(payload, str) or not payload.strip():
            return None
        return {"type": "postback", "title": button["title"], "payload": payload.strip()}

    @classmethod
    def _cards_to_template_payload(cls, payload: OmnichannelCardsReply) -> dict[str, object]:
        elements: list[dict[str, object]] = []
        for card in payload["cards"]:
            element: dict[str, object] = {"title": card["title"]}
            subtitle = card.get("subtitle")
            if isinstance(subtitle, str) and subtitle.strip():
                element["subtitle"] = subtitle.strip()
            image_url = card.get("image_url")
            if isinstance(image_url, str) and image_url.strip():
                element["image_url"] = image_url.strip()
            default_url = card.get("default_url")
            if isinstance(default_url, str) and default_url.strip():
                element["default_action"] = {
                    "type": "web_url",
                    "url": default_url.strip(),
                }
            card_buttons = card.get("buttons") or []
            buttons = [mapped for button in card_buttons if (mapped := cls._to_messenger_card_button(button))]
            if buttons:
                element["buttons"] = buttons
            elements.append(element)
        return {"template_type": "generic", "elements": elements}

    @classmethod
    def _to_messenger_payload(cls, payload: OmnichannelReplyPayload) -> dict[str, object]:
        if payload["type"] == "cards":
            cards_payload: OmnichannelCardsReply = payload
            template_payload = cls._cards_to_template_payload(cards_payload)
            converted: dict[str, object] = {
                "type": "template",
                "template_payload": template_payload,
            }
            intro = payload.get("text")
            if isinstance(intro, str) and intro.strip():
                converted["intro_text"] = intro.strip()
            buttons = payload.get("buttons")
            if isinstance(buttons, list) and buttons:
                converted["followup_actions"] = buttons
            return converted
        if payload["type"] == "actions":
            quick_replies = []
            for button in payload["buttons"]:
                item: dict[str, str] = {
                    "content_type": "text",
                    "title": button["title"],
                    "payload": button.get("payload") or button.get("url") or button["title"],
                }
                image_url = button.get("image_url")
                if isinstance(image_url, str) and image_url.strip():
                    item["image_url"] = image_url.strip()
                quick_replies.append(item)
            return {
                "type": "quick_replies",
                "text": payload["text"],
                "quick_replies": quick_replies,
            }
        return dict(payload)

    @classmethod
    def send(
        cls,
        *,
        recipient_id: str,
        payload: OmnichannelReplyPayload,
        channel_config: dict[str, str],
        delivery: str = "standard",
    ) -> OmnichannelReplySendResult:
        from services.omnichannel.messenger_graph_send import MessengerSendDelivery
        from services.omnichannel.messenger_runtime_service import MessengerRuntimeService

        send_delivery: MessengerSendDelivery = "human_agent" if delivery == "human_agent" else "standard"

        intro_text = ""
        followup_actions: list[OmnichannelButton] | None = None
        if payload["type"] == "cards":
            intro = payload.get("text")
            if isinstance(intro, str):
                intro_text = intro.strip()
            buttons = payload.get("buttons")
            if isinstance(buttons, list) and buttons:
                followup_actions = buttons

        converted = cls._to_messenger_payload(payload)
        sent = False

        if intro_text:
            MessengerRuntimeService._send_text_reply(
                recipient_id, intro_text, channel_config, delivery=send_delivery
            )
            sent = True

        converted_type = converted.get("type")
        if converted_type == "template":
            template_payload = converted.get("template_payload")
            if isinstance(template_payload, dict) and template_payload:
                MessengerRuntimeService._send_template_reply(
                    recipient_id,
                    template_payload,
                    channel_config,
                    delivery=send_delivery,
                )
                sent = True
        elif converted_type == "quick_replies":
            message_text = converted.get("text")
            quick_replies = converted.get("quick_replies")
            if (
                isinstance(message_text, str)
                and message_text.strip()
                and isinstance(quick_replies, list)
                and quick_replies
            ):
                MessengerRuntimeService._send_quick_replies_reply(
                    recipient_id,
                    message_text.strip(),
                    quick_replies,  # type: ignore[arg-type]
                    channel_config,
                    delivery=send_delivery,
                )
                sent = True

        if followup_actions:
            MessengerRuntimeService._send_quick_replies_reply(
                recipient_id,
                "Chọn thêm:",
                [
                    {
                        "content_type": "text",
                        "title": button["title"],
                        "payload": button.get("payload") or button.get("url") or button["title"],
                    }
                    for button in followup_actions
                ],  # type: ignore[arg-type]
                channel_config,
                delivery=send_delivery,
            )
            sent = True

        return {
            "sent": sent,
            "external_message_ids": [],
            "inbox_content": OmnichannelReplyPayloadService.to_inbox_content(payload),
        }


class ZaloPersonalReplyAdapter:
    @classmethod
    def _send_part(
        cls,
        *,
        channel_id: str,
        thread_id: str,
        text: str,
        image_urls: list[str],
    ) -> None:
        try:
            ZaloPersonalSessionService.send_rich_message(
                channel_id=channel_id,
                thread_id=thread_id,
                text=text,
                image_urls=image_urls,
            )
            return
        except Exception:
            if not image_urls:
                raise
            logger.warning(
                "Zalo personal image send failed channel=%s thread=%s; falling back to links",
                channel_id,
                thread_id,
                exc_info=True,
            )
            fallback_lines: list[str] = []
            if text:
                fallback_lines.append(text)
            for url in image_urls:
                if url not in text:
                    fallback_lines.append(url)
            ZaloPersonalSessionService.send_rich_message(
                channel_id=channel_id,
                thread_id=thread_id,
                text="\n".join(fallback_lines),
                image_urls=[],
            )

    @classmethod
    def send(
        cls,
        *,
        channel_id: str,
        recipient_id: str,
        payload: OmnichannelReplyPayload,
        channel_config: dict[str, Any] | None = None,
    ) -> OmnichannelReplySendResult:
        from services.omnichannel.zalo_personal_presence_service import ZaloPersonalPresenceService
        from services.omnichannel.zalo_personal_reply_format import (
            ZaloPersonalReplyFormatService,
        )

        cfg = channel_config or {}
        if payload["type"] == "sender_action":
            action = payload["action"]
            if action == "typing_on":
                ZaloPersonalPresenceService.send_typing(channel_id=channel_id, thread_id=recipient_id)
            return {"sent": False, "external_message_ids": [], "inbox_content": ""}

        parts = ZaloPersonalReplyFormatService.split_payload(payload)
        if not parts:
            return {"sent": False, "external_message_ids": [], "inbox_content": ""}

        inbox_content = ZaloPersonalReplyFormatService.to_inbox_content(parts)
        presence_opts = cfg.get("presence")
        presence_options = presence_opts if isinstance(presence_opts, dict) else None
        ZaloPersonalPresenceService.prepare_before_send(
            channel_id=channel_id,
            thread_id=recipient_id,
            reply_text=inbox_content,
            tenant_id=str(cfg.get("tenant_id") or "") or None,
            conversation_id=str(cfg.get("conversation_id") or "") or None,
            message_meta=cfg.get("message_meta") if isinstance(cfg.get("message_meta"), dict) else None,
            options=presence_options,
        )

        sent = False
        for part in parts:
            text = (part.get("text") or "").strip()
            image_urls = [url for url in (part.get("image_urls") or []) if str(url).strip()]
            if not text and not image_urls:
                continue
            try:
                cls._send_part(
                    channel_id=channel_id,
                    thread_id=recipient_id,
                    text=text,
                    image_urls=image_urls,
                )
                sent = True
            except Exception:
                logger.exception(
                    "Zalo personal auto-reply part failed channel=%s thread=%s",
                    channel_id,
                    recipient_id,
                )

        return {
            "sent": sent,
            "external_message_ids": [],
            "inbox_content": inbox_content,
        }


class OmnichannelReplySenderService:
    @classmethod
    def send_parsed(
        cls,
        *,
        channel_type: str,
        recipient_id: str,
        payload: OmnichannelReplyPayload,
        channel_config: dict[str, Any],
        quote_message_id: str | None = None,
        delivery: str = "standard",
    ) -> OmnichannelReplySendResult:
        from models.trigger import OmniChannelType

        if channel_type == OmniChannelType.ZALO_OA:
            token = str(channel_config.get("oa_access_token") or "").strip()
            if not token:
                raise ValueError("Zalo OA access token is missing")
            return ZaloOaReplyAdapter.send(
                sender=ZaloOaSender(token),
                recipient_id=recipient_id,
                payload=payload,
                quote_message_id=quote_message_id,
            )

        if channel_type in {
            OmniChannelType.FACEBOOK_MESSENGER,
            OmniChannelType.INSTAGRAM_DM,
            OmniChannelType.TIKTOK_MESSAGING,
        }:
            from services.omnichannel.messenger_runtime_service import MessengerRuntimeService

            messenger_config = {
                "app_id": str(channel_config.get("app_id") or ""),
                "page_access_token": str(channel_config.get("page_access_token") or ""),
                "graph_api_version": str(channel_config.get("graph_api_version") or "v23.0"),
            }
            if payload["type"] == "sender_action":
                MessengerRuntimeService._send_sender_action(
                    recipient_psid=recipient_id,
                    action=payload["action"],
                    channel_config=messenger_config,
                )
                return {"sent": False, "external_message_ids": [], "inbox_content": ""}
            return MessengerReplyAdapter.send(
                recipient_id=recipient_id,
                payload=payload,
                channel_config=messenger_config,
                delivery=delivery,
            )

        if channel_type == OmniChannelType.ZALO_PERSONAL:
            return ZaloPersonalReplyAdapter.send(
                channel_id=str(channel_config.get("channel_id") or ""),
                recipient_id=recipient_id,
                payload=payload,
                channel_config=channel_config,
            )

        raise ValueError(f"Unsupported channel type for rich replies: {channel_type}")

    @classmethod
    def send(
        cls,
        *,
        channel_type: str,
        recipient_id: str,
        reply_text: str,
        channel_config: dict[str, Any],
        quote_message_id: str | None = None,
    ) -> OmnichannelReplySendResult:
        payload = OmnichannelReplyPayloadService.parse(reply_text)
        return cls.send_parsed(
            channel_type=channel_type,
            recipient_id=recipient_id,
            payload=payload,
            channel_config=channel_config,
            quote_message_id=quote_message_id,
        )
