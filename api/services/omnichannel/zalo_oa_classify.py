"""Zalo OA webhook classification (ported from zca-bridge src/zalo-oa/classify.ts)."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from services.omnichannel.messenger_service import OmniChannelIncomingAttachment, OmniChannelIncomingEvent

MediaKind = Literal["image", "audio", "video", "file"]

_SELF_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "oa_send_text",
        "oa_send_image",
        "oa_send_file",
        "oa_send_gif",
        "oa_send_sticker",
    }
)

_MEDIA_ICON: dict[MediaKind, str] = {
    "image": "🖼️",
    "audio": "🎙️",
    "video": "🎥",
    "file": "📎",
}

_SELF_PREFIX = "📱 từ app Zalo"


class ZaloOaWebhookEvent(OmniChannelIncomingEvent):
    """Extended omnichannel event with Zalo OA bridge fields."""

    is_self: NotRequired[bool]
    event_name: NotRequired[str]
    quote_message_id: NotRequired[str]


class _ClassifiedText(TypedDict):
    kind: Literal["text"]
    text: str


class _ClassifiedMedia(TypedDict):
    kind: Literal["media"]
    media_type: MediaKind
    href: str
    filename: str
    caption: str


class _ClassifiedFallback(TypedDict):
    kind: Literal["fallback"]
    text: str


_ClassifiedMessage = _ClassifiedText | _ClassifiedMedia | _ClassifiedFallback


def _fetchable(href: str) -> bool:
    return href.lower().startswith("http://") or href.lower().startswith("https://")


def _media_of(media_type: MediaKind, href: str, filename: str, caption: str) -> _ClassifiedMessage:
    if _fetchable(href):
        return {
            "kind": "media",
            "media_type": media_type,
            "href": href,
            "filename": filename,
            "caption": caption,
        }
    return {"kind": "fallback", "text": f"[{media_type}]"}


def _classify_content(event_name: str, message: dict[str, Any] | None) -> _ClassifiedMessage:
    text = str((message or {}).get("text") or "")
    attachments = (message or {}).get("attachments") or []
    att = attachments[0] if attachments else {}
    payload = att.get("payload") if isinstance(att, dict) else {}
    url = str((payload or {}).get("url") or "") if isinstance(payload, dict) else ""
    att_type = str((att or {}).get("type") or "").lower() if isinstance(att, dict) else ""

    if event_name in {"user_send_text", "user_send_link", "oa_send_text"}:
        return {"kind": "text", "text": text or url}
    if event_name in {"user_send_image", "user_send_gif", "user_send_sticker", "oa_send_image"}:
        name = url.split("/")[-1].split("?")[0] if url else "image.jpg"
        return _media_of("image", url, name or "image.jpg", text)
    if event_name == "user_send_audio":
        return _media_of("audio", url, "audio.m4a", "")
    if event_name == "user_send_video":
        return _media_of("video", url, "video.mp4", text)
    if event_name in {"user_send_file", "oa_send_file"}:
        name = str((payload or {}).get("name") or "") if isinstance(payload, dict) else ""
        if not name and url:
            name = url.split("/")[-1].split("?")[0]
        return _media_of("file", url, name or "file", "")
    if event_name == "user_send_location":
        coords = (payload or {}).get("coordinates") if isinstance(payload, dict) else {}
        if isinstance(coords, dict):
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            if lat is not None and lon is not None:
                return {
                    "kind": "fallback",
                    "text": f"📍 Vị trí: https://www.google.com/maps?q={lat},{lon}",
                }
        return {"kind": "fallback", "text": "📍 Vị trí"}
    return {
        "kind": "fallback",
        "text": f"[Tin OA loại {event_name or 'không rõ'} — mở app để xem]",
    }


def _classified_to_content(classified: _ClassifiedMessage) -> tuple[str, list[OmniChannelIncomingAttachment]]:
    if classified["kind"] == "text":
        return classified["text"], []
    if classified["kind"] == "media":
        icon = _MEDIA_ICON.get(classified["media_type"], "📎")
        content = classified["caption"] or f"{icon} {classified['media_type']}"
        return content, [{"type": classified["media_type"], "url": classified["href"]}]
    return classified["text"], []


def classify_oa_webhook_event(channel_id: str, payload: dict[str, Any], *, is_self: bool) -> ZaloOaWebhookEvent | None:
    """Normalize one Zalo OA webhook JSON body to a bridge-style omnichannel event."""
    event_name = str(payload.get("event_name") or payload.get("event") or "").strip()
    if not event_name:
        return None

    sender_obj = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
    recipient_obj = payload.get("recipient") if isinstance(payload.get("recipient"), dict) else {}
    message_obj = payload.get("message") if isinstance(payload.get("message"), dict) else {}

    user_id = (
        str(recipient_obj.get("id") or "").strip()
        if is_self
        else str(sender_obj.get("id") or sender_obj.get("user_id") or sender_obj.get("uid") or "").strip()
    )
    if not user_id:
        return None

    oa_id = str(
        payload.get("oa_id")
        or (sender_obj.get("id") if is_self else recipient_obj.get("id"))
        or payload.get("appid")
        or ""
    ).strip()
    msg_id = str(message_obj.get("msg_id") or "").strip()
    quote_msg_id = str(message_obj.get("quote_msg_id") or "").strip()

    classified = _classify_content(event_name, message_obj)
    content, attachments = _classified_to_content(classified)
    if not content.strip() and not attachments:
        return None

    event: ZaloOaWebhookEvent = {
        "channel": "zalo_oa",
        "channel_id": channel_id,
        "external_account_id": oa_id,
        "external_user_id": user_id,
        "text": content,
        "raw_event": payload,
        "is_self": is_self,
        "event_name": event_name,
    }
    if msg_id:
        event["message_id"] = msg_id
    if attachments:
        event["attachments"] = attachments
    if quote_msg_id:
        event["quote_message_id"] = quote_msg_id
    return event


def is_self_oa_event(event_name: str) -> bool:
    return event_name in _SELF_EVENT_NAMES


def should_enqueue_oa_webhook(event_name: str) -> bool:
    """Return True when the webhook should create an inbox message."""
    if not event_name:
        return False
    if event_name.startswith("user_send_"):
        return True
    return is_self_oa_event(event_name)


def format_self_outbound_content(content: str) -> str:
    body = (content or "").strip()
    if body:
        return f"{_SELF_PREFIX}\n{body}"
    return _SELF_PREFIX
