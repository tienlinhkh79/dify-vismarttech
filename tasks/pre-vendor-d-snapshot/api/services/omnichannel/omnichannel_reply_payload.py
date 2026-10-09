"""Provider-agnostic rich reply parsing for omnichannel outbound messages.

Dify apps can return either plain text or a JSON object. The canonical schema
supports cards (carousel/list), action buttons, attachments, and legacy
Messenger-specific shapes for backward compatibility.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, NotRequired, TypedDict

_MAX_CARDS = 10
_MAX_ZALO_CARDS = 5
_MAX_BUTTONS = 13
_MAX_ZALO_BUTTONS = 4


class OmnichannelButton(TypedDict):
    title: str
    action: Literal["url", "postback"]
    url: NotRequired[str]
    payload: NotRequired[str]
    image_url: NotRequired[str]


class OmnichannelCard(TypedDict):
    title: str
    subtitle: NotRequired[str]
    image_url: NotRequired[str]
    default_url: NotRequired[str]
    buttons: NotRequired[list[OmnichannelButton]]


class OmnichannelTextReply(TypedDict):
    type: Literal["text"]
    text: str


class OmnichannelAttachmentReply(TypedDict):
    type: Literal["attachment"]
    attachment_type: Literal["image", "video", "audio", "file"]
    url: str


class OmnichannelActionsReply(TypedDict):
    type: Literal["actions"]
    text: str
    buttons: list[OmnichannelButton]


class OmnichannelCardsReply(TypedDict):
    type: Literal["cards"]
    text: NotRequired[str]
    cards: list[OmnichannelCard]
    buttons: NotRequired[list[OmnichannelButton]]


class OmnichannelSenderActionReply(TypedDict):
    type: Literal["sender_action"]
    action: Literal["typing_on", "typing_off", "mark_seen"]


class OmnichannelLegacyQuickRepliesReply(TypedDict):
    type: Literal["quick_replies"]
    text: str
    quick_replies: list[dict[str, str]]


class OmnichannelLegacyTemplateReply(TypedDict):
    type: Literal["template"]
    template_payload: dict[str, Any]


OmnichannelReplyPayload = (
    OmnichannelTextReply
    | OmnichannelAttachmentReply
    | OmnichannelActionsReply
    | OmnichannelCardsReply
    | OmnichannelSenderActionReply
    | OmnichannelLegacyQuickRepliesReply
    | OmnichannelLegacyTemplateReply
)


class OmnichannelReplyPayloadService:
    @staticmethod
    def normalize_llm_text(text: str) -> str:
        value = text.strip()
        value = re.sub(r"^\s*text\s*:\s*", "", value, flags=re.IGNORECASE)
        if value.startswith("```") and value.endswith("```"):
            value = value[3:-3].strip()
        return value

    @staticmethod
    def strip_markdown_for_messaging(text: str) -> str:
        value = OmnichannelReplyPayloadService.normalize_llm_text(text)
        value = re.sub(r"```[^\n]*\n?", "", value)
        value = re.sub(r"```", "", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
        value = re.sub(r"\*([^*]+)\*", r"\1", value)
        value = re.sub(r"__([^_]+)__", r"\1", value)
        value = re.sub(r"_([^_]+)_", r"\1", value)
        value = re.sub(r"^#{1,6}\s+", "", value, flags=re.MULTILINE)
        value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", value)
        value = re.sub(r"^[\-*]\s+", "• ", value, flags=re.MULTILINE)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    @staticmethod
    def extract_markdown_image_urls(text: str) -> tuple[str, list[str]]:
        pattern = re.compile(r"!\[[^\]]*]\((https?://[^\s)]+)\)")
        image_urls = [match.group(1).strip() for match in pattern.finditer(text) if match.group(1).strip()]
        cleaned = pattern.sub("", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned, image_urls

    @classmethod
    def parse(cls, reply_text: str) -> OmnichannelReplyPayload:
        normalized = cls.normalize_llm_text(reply_text)
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError:
            plain = cls.strip_markdown_for_messaging(normalized)
            return {"type": "text", "text": plain}

        if not isinstance(data, dict):
            plain = cls.strip_markdown_for_messaging(normalized)
            return {"type": "text", "text": plain}

        reply_type = data.get("type")
        if reply_type == "cards":
            parsed = cls._parse_cards(data)
            if parsed:
                return parsed
        if reply_type == "actions":
            parsed = cls._parse_actions(data)
            if parsed:
                return parsed
        if reply_type == "attachment":
            parsed = cls._parse_attachment(data)
            if parsed:
                return parsed
        if reply_type == "quick_replies":
            parsed = cls._parse_legacy_quick_replies(data)
            if parsed:
                return parsed
        if reply_type == "template":
            template_payload = data.get("template_payload")
            if isinstance(template_payload, dict) and template_payload:
                return {"type": "template", "template_payload": template_payload}
        if reply_type == "sender_action":
            action = data.get("action")
            if isinstance(action, str) and action in {"typing_on", "typing_off", "mark_seen"}:
                return {"type": "sender_action", "action": action}
        if reply_type == "text":
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                return {"type": "text", "text": cls.strip_markdown_for_messaging(text)}

        plain = cls.strip_markdown_for_messaging(normalized)
        return {"type": "text", "text": plain}

    @classmethod
    def to_inbox_content(cls, payload: OmnichannelReplyPayload) -> str:
        if payload["type"] == "text":
            return payload["text"]
        if payload["type"] == "attachment":
            return payload["url"].strip()
        if payload["type"] == "actions":
            lines = [payload["text"]]
            lines.extend(f"• {button['title']}" for button in payload["buttons"])
            return "\n".join(lines)
        if payload["type"] == "cards":
            lines: list[str] = []
            intro = payload.get("text")
            if isinstance(intro, str) and intro.strip():
                lines.append(intro.strip())
            for card in payload["cards"]:
                line = card["title"]
                subtitle = card.get("subtitle")
                if isinstance(subtitle, str) and subtitle.strip():
                    line = f"{line} — {subtitle.strip()}"
                lines.append(f"• {line}")
            buttons = payload.get("buttons") or []
            for button in buttons:
                lines.append(f"• {button['title']}")
            return "\n".join(lines)
        if payload["type"] == "quick_replies":
            lines = [payload["text"]]
            for item in payload["quick_replies"]:
                title = item.get("title")
                if isinstance(title, str) and title.strip():
                    lines.append(f"• {title.strip()}")
            return "\n".join(lines)
        if payload["type"] == "template":
            return json.dumps(payload["template_payload"], ensure_ascii=False)
        return ""

    @staticmethod
    def _parse_button(item: object) -> OmnichannelButton | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            return None
        action = item.get("action")
        url = item.get("url")
        payload = item.get("payload")
        if action == "url" or (isinstance(url, str) and url.strip()):
            if not isinstance(url, str) or not url.strip():
                return None
            button: OmnichannelButton = {"title": title.strip(), "action": "url", "url": url.strip()}
            image_url = item.get("image_url")
            if isinstance(image_url, str) and image_url.strip():
                button["image_url"] = image_url.strip()
            return button
        if action == "postback" or (isinstance(payload, str) and payload.strip()):
            if not isinstance(payload, str) or not payload.strip():
                return None
            button = {"title": title.strip(), "action": "postback", "payload": payload.strip()}
            image_url = item.get("image_url")
            if isinstance(image_url, str) and image_url.strip():
                button["image_url"] = image_url.strip()
            return button
        return None

    @classmethod
    def _parse_card(cls, item: object) -> OmnichannelCard | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            return None
        card: OmnichannelCard = {"title": title.strip()}
        subtitle = item.get("subtitle")
        if isinstance(subtitle, str) and subtitle.strip():
            card["subtitle"] = subtitle.strip()
        image_url = item.get("image_url")
        if isinstance(image_url, str) and image_url.strip():
            card["image_url"] = image_url.strip()
        default_url = item.get("default_url")
        if isinstance(default_url, str) and default_url.strip():
            card["default_url"] = default_url.strip()
        raw_buttons = item.get("buttons")
        if isinstance(raw_buttons, list):
            buttons = [btn for raw in raw_buttons if (btn := cls._parse_button(raw))]
            if buttons:
                card["buttons"] = buttons[:3]
        return card

    @classmethod
    def _parse_cards(cls, data: dict[str, Any]) -> OmnichannelCardsReply | None:
        raw_cards = data.get("cards")
        if not isinstance(raw_cards, list):
            return None
        cards = [card for raw in raw_cards if (card := cls._parse_card(raw))]
        if not cards:
            return None
        payload: OmnichannelCardsReply = {"type": "cards", "cards": cards[:_MAX_CARDS]}
        intro = data.get("text")
        if isinstance(intro, str) and intro.strip():
            payload["text"] = cls.strip_markdown_for_messaging(intro)
        raw_buttons = data.get("buttons")
        if isinstance(raw_buttons, list):
            buttons = [btn for raw in raw_buttons if (btn := cls._parse_button(raw))]
            if buttons:
                payload["buttons"] = buttons[:_MAX_BUTTONS]
        return payload

    @classmethod
    def _parse_actions(cls, data: dict[str, Any]) -> OmnichannelActionsReply | None:
        text = data.get("text")
        raw_buttons = data.get("buttons")
        if not isinstance(text, str) or not text.strip() or not isinstance(raw_buttons, list):
            return None
        buttons = [btn for raw in raw_buttons if (btn := cls._parse_button(raw))]
        if not buttons:
            return None
        return {
            "type": "actions",
            "text": cls.strip_markdown_for_messaging(text),
            "buttons": buttons[:_MAX_BUTTONS],
        }

    @staticmethod
    def _parse_attachment(data: dict[str, Any]) -> OmnichannelAttachmentReply | None:
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
        return None

    @classmethod
    def _parse_legacy_quick_replies(cls, data: dict[str, Any]) -> OmnichannelLegacyQuickRepliesReply | None:
        text = data.get("text")
        quick_replies = data.get("quick_replies")
        if not isinstance(text, str) or not text.strip() or not isinstance(quick_replies, list):
            return None
        normalized: list[dict[str, str]] = []
        for item in quick_replies:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            payload = item.get("payload")
            if isinstance(title, str) and title.strip() and isinstance(payload, str) and payload.strip():
                entry: dict[str, str] = {
                    "content_type": "text",
                    "title": title.strip(),
                    "payload": payload.strip(),
                }
                image_url = item.get("image_url")
                if isinstance(image_url, str) and image_url.strip():
                    entry["image_url"] = image_url.strip()
                normalized.append(entry)
        if not normalized:
            return None
        return {
            "type": "quick_replies",
            "text": cls.strip_markdown_for_messaging(text),
            "quick_replies": normalized[:_MAX_BUTTONS],
        }


def zalo_button_limit() -> int:
    return _MAX_ZALO_BUTTONS


def zalo_card_limit() -> int:
    return _MAX_ZALO_CARDS
