"""Build workflow ``inputs`` and ``query`` from normalized omnichannel inbound events."""

from __future__ import annotations

from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey

_BUTTON_INTERACTION_TYPES = frozenset({"postback", "quick_reply", "button_click"})


def build_workflow_start_inputs(
    *,
    channel_id: str,
    channel_type: str,
    conversation_id: str,
    external_user_id: str,
    event: OmniChannelIncomingEvent | None = None,
) -> dict[str, str]:
    inputs: dict[str, str] = {
        OmnichannelAppStartInputKey.CHANNEL_ID: channel_id,
        OmnichannelAppStartInputKey.CHANNEL_TYPE: channel_type,
        OmnichannelAppStartInputKey.CONVERSATION_ID: conversation_id,
        OmnichannelAppStartInputKey.EXTERNAL_USER_ID: external_user_id,
    }
    if not event:
        return inputs

    interaction_type = str(event.get("interaction_type") or "message").strip() or "message"
    inputs[OmnichannelAppStartInputKey.INTERACTION_TYPE] = interaction_type

    button_payload = str(event.get("button_payload") or "").strip()
    if button_payload:
        inputs[OmnichannelAppStartInputKey.BUTTON_PAYLOAD] = button_payload

    button_title = str(event.get("button_title") or "").strip()
    if button_title:
        inputs[OmnichannelAppStartInputKey.BUTTON_TITLE] = button_title

    return inputs


def build_event_query(event: OmniChannelIncomingEvent) -> str:
    """Prefer structured button payload for workflow routing (Switch / IF nodes)."""
    interaction_type = str(event.get("interaction_type") or "").strip()
    button_payload = str(event.get("button_payload") or "").strip()
    button_title = str(event.get("button_title") or "").strip()

    if button_payload and interaction_type in _BUTTON_INTERACTION_TYPES:
        if button_title and button_title != button_payload:
            return f"{button_title} ({button_payload})"
        return button_payload

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
