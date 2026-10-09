"""Format rich omnichannel payloads for Zalo Personal (text menus + image messages)."""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import urlparse

from services.omnichannel.omnichannel_reply_payload import (
    OmnichannelButton,
    OmnichannelCard,
    OmnichannelReplyPayload,
)

_MENU_FOOTER = "👉 Gõ số để chọn (ví dụ: 1 hoặc 2)."


class ZaloPersonalOutboundPart(TypedDict):
    text: str
    image_urls: list[str]


class ZaloPersonalReplyFormatService:
    @classmethod
    def split_payload(cls, payload: OmnichannelReplyPayload) -> list[ZaloPersonalOutboundPart]:
        if payload["type"] == "text":
            text = payload["text"].strip()
            return [{"text": text, "image_urls": []}] if text else []
        if payload["type"] == "attachment":
            url = payload["url"].strip()
            if payload["attachment_type"] == "image" and url:
                return [{"text": "", "image_urls": [url]}]
            return [{"text": url, "image_urls": []}] if url else []
        if payload["type"] == "actions":
            return cls._format_actions(payload["text"], payload["buttons"])
        if payload["type"] == "cards":
            return cls._format_cards(payload)
        if payload["type"] == "quick_replies":
            buttons = [
                {
                    "title": str(item.get("title") or ""),
                    "action": "postback",
                    "payload": str(item.get("payload") or item.get("title") or ""),
                }
                for item in payload["quick_replies"]
                if str(item.get("title") or "").strip()
            ]
            return cls._format_actions(payload["text"], buttons)  # type: ignore[arg-type]
        plain = payload.get("text") if isinstance(payload, dict) else None  # type: ignore[union-attr]
        if isinstance(plain, str) and plain.strip():
            return [{"text": plain.strip(), "image_urls": []}]
        return []

    @classmethod
    def to_inbox_content(cls, parts: list[ZaloPersonalOutboundPart]) -> str:
        lines: list[str] = []
        for part in parts:
            text = (part.get("text") or "").strip()
            if text:
                lines.append(text)
            for url in part.get("image_urls") or []:
                if url.strip():
                    lines.append(url.strip())
        return "\n\n".join(lines)

    @classmethod
    def _format_actions(cls, intro: str, buttons: list[OmnichannelButton]) -> list[ZaloPersonalOutboundPart]:
        body = (intro or "").strip()
        lines: list[str] = []
        if body:
            lines.append(body)
            lines.append("")
        for index, button in enumerate(buttons, start=1):
            lines.append(cls._format_menu_line(index, button))
        lines.extend(["", _MENU_FOOTER])
        return [{"text": "\n".join(lines), "image_urls": []}]

    @classmethod
    def _format_menu_line(cls, index: int, button: OmnichannelButton) -> str:
        title = button["title"].strip()
        if button["action"] == "url":
            url = str(button.get("url") or "").strip()
            if url:
                return f"{index}. {title} — {cls._short_link_display(url)}"
            return f"{index}. {title}"
        return f"{index}. {title}"

    @classmethod
    def _format_cards(cls, payload: OmnichannelReplyPayload) -> list[ZaloPersonalOutboundPart]:
        if payload["type"] != "cards":
            return []
        parts: list[ZaloPersonalOutboundPart] = []
        intro_raw = payload.get("text")
        intro = intro_raw.strip() if isinstance(intro_raw, str) else ""

        cards: list[OmnichannelCard] = payload["cards"]
        cards_with_images = [
            card for card in cards if str(card.get("image_url") or "").strip()
        ]
        if cards_with_images:
            for index, card in enumerate(cards_with_images):
                image_url = str(card.get("image_url") or "").strip()
                caption = cls._compact_image_caption(card)
                if index == 0 and intro:
                    caption = f"{intro}\n\n{caption}"
                parts.append({"text": caption, "image_urls": [image_url]})
        else:
            lines: list[str] = []
            if intro:
                lines.extend([intro, ""])
            for card in cards:
                caption = cls._card_caption_text_only(card)
                if caption:
                    lines.append(caption)
                    lines.append("")
            body = "\n".join(lines).strip()
            if body:
                parts.append({"text": body, "image_urls": []})

        footer_buttons = payload.get("buttons") or []
        if footer_buttons:
            parts.extend(cls._format_actions("Bạn muốn tiếp theo:", footer_buttons))
        elif len(cards) > 1 and not cards_with_images:
            lines = ["📋 Chọn sản phẩm:"]
            for index, card in enumerate(cards, start=1):
                line = f"{index}. {card['title'].strip()}"
                subtitle = card.get("subtitle")
                if isinstance(subtitle, str) and subtitle.strip():
                    line = f"{line} — {subtitle.strip()}"
                lines.append(line)
            lines.extend(["", _MENU_FOOTER])
            parts.append({"text": "\n".join(lines), "image_urls": []})
        return parts

    @classmethod
    def _compact_image_caption(cls, card: OmnichannelCard) -> str:
        lines = [card["title"].strip()]
        subtitle = card.get("subtitle")
        if isinstance(subtitle, str) and subtitle.strip():
            lines.append(subtitle.strip())
        return "\n".join(lines)

    @classmethod
    def _card_caption_text_only(cls, card: OmnichannelCard) -> str:
        lines = [card["title"].strip()]
        subtitle = card.get("subtitle")
        if isinstance(subtitle, str) and subtitle.strip():
            lines.append(subtitle.strip())
        card_buttons = card.get("buttons") or []
        for button in card_buttons:
            if button["action"] == "url":
                url = str(button.get("url") or card.get("default_url") or "").strip()
                if url:
                    lines.append(f"👉 {button['title'].strip()}: {cls._short_link_display(url)}")
            else:
                lines.append(f"• {button['title'].strip()}")
        return "\n".join(lines)

    @classmethod
    def _short_link_display(cls, url: str) -> str:
        raw = url.strip()
        if not raw:
            return ""
        parsed = urlparse(raw)
        if not parsed.netloc:
            return raw
        path = (parsed.path or "").rstrip("/")
        if parsed.query:
            path = f"{path}?…"
        display = f"{parsed.netloc}{path}"
        if len(display) > 52:
            return f"{display[:49]}…"
        return display
