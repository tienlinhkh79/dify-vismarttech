"""Messenger adapter primitives for omnichannel webhook ingestion.

This module provides narrowly scoped helpers to verify Messenger requests and
normalize Messenger payloads into a common omnichannel event shape. The first
version intentionally only covers text message ingestion and the verification
flow, so other channels can reuse the same normalized contract later.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, NotRequired, TypedDict


class OmniChannelIncomingAttachment(TypedDict):
    type: str
    url: str


class OmniChannelIncomingEvent(TypedDict):
    """Canonical inbound message event used by omnichannel adapters."""

    channel: str
    channel_id: str
    external_account_id: str
    external_user_id: str
    text: str
    message_id: NotRequired[str]
    attachments: NotRequired[list[OmniChannelIncomingAttachment]]
    raw_event: dict[str, Any]


class MessengerService:
    """Service that validates and normalizes Facebook Messenger webhook data."""

    @staticmethod
    def verify_webhook_handshake(
        mode: str | None, verify_token: str | None, challenge: str | None, expected_token: str
    ) -> str:
        """Validate Messenger webhook handshake and return the challenge token.

        Raises:
            ValueError: If the handshake payload is missing required fields or
            verify token does not match.
        """
        if mode != "subscribe":
            raise ValueError("Invalid webhook mode")
        if not challenge:
            raise ValueError("Missing webhook challenge")
        if verify_token != expected_token:
            raise ValueError("Invalid webhook verify token")
        return challenge

    @staticmethod
    def verify_payload_signature(signature_header: str | None, payload: bytes, app_secret: str | None) -> bool:
        """Check `X-Hub-Signature-256` against the configured app secret.

        Signature format: ``sha256=<hex-digest>``.
        """
        if not app_secret or not signature_header:
            return False
        prefix = "sha256="
        if not signature_header.startswith(prefix):
            return False

        expected_digest = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        provided_digest = signature_header[len(prefix) :]
        return hmac.compare_digest(expected_digest, provided_digest)

    @staticmethod
    def parse_message_events(channel_id: str, payload: dict[str, Any]) -> list[OmniChannelIncomingEvent]:
        """Normalize Messenger payload to canonical omnichannel events.

        User text messages and image/file attachments are emitted.
        Delivery/read/postback events are ignored.
        """
        events: list[OmniChannelIncomingEvent] = []
        for entry in payload.get("entry", []):
            entry_id = str(entry.get("id", ""))
            for messaging_event in entry.get("messaging", []):
                message = messaging_event.get("message") or {}
                if bool(message.get("is_echo")):
                    continue
                text = str(message.get("text") or "").strip()
                sender_id = (messaging_event.get("sender") or {}).get("id")
                if not sender_id:
                    continue
                if str(sender_id) == entry_id:
                    # Ignore outbound page echoes to avoid reply loops.
                    continue

                attachments: list[OmniChannelIncomingAttachment] = []
                for item in message.get("attachments") or []:
                    if not isinstance(item, dict):
                        continue
                    attachment_type = str(item.get("type") or "").strip()
                    payload_obj = item.get("payload") or {}
                    if not isinstance(payload_obj, dict):
                        continue
                    attachment_url = str(payload_obj.get("url") or "").strip()
                    if not attachment_type or not attachment_url:
                        continue
                    attachments.append({"type": attachment_type, "url": attachment_url})

                if not text and not attachments:
                    continue

                event: OmniChannelIncomingEvent = {
                    "channel": "facebook_messenger",
                    "channel_id": channel_id,
                    "external_account_id": entry_id,
                    "external_user_id": str(sender_id),
                    "text": text,
                    "raw_event": messaging_event,
                }
                if "mid" in message:
                    event["message_id"] = str(message["mid"])
                if attachments:
                    event["attachments"] = attachments
                events.append(event)

        return events
