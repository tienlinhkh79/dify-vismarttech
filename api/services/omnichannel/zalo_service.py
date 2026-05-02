"""Zalo OA adapter primitives for omnichannel webhook ingestion."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, TypedDict

from services.omnichannel.messenger_service import OmniChannelIncomingEvent

logger = logging.getLogger(__name__)


class ZaloWebhookPayload(TypedDict, total=False):
    app_id: str
    timestamp: str | int


class ZaloService:
    """Service that validates and normalizes Zalo OA webhook data."""

    @staticmethod
    def verify_webhook_handshake(
        verify_token: str | None,
        challenge: str | None,
        expected_token: str,
    ) -> str:
        """Validate optional handshake flow and return challenge token."""
        if not challenge:
            raise ValueError("Missing webhook challenge")
        if verify_token != expected_token:
            raise ValueError("Invalid webhook verify token")
        return challenge

    @staticmethod
    def verify_event_signature(
        signature_header: str | None,
        payload_bytes: bytes,
        app_secret: str | None,
        app_id: str | None,
        timestamp: str | int | None,
    ) -> bool:
        """Validate Zalo webhook signature when signature header is present."""
        if not signature_header:
            # Some sandbox integrations forward events without signature.
            return True
        if not app_secret:
            return False

        payload_text = payload_bytes.decode("utf-8", errors="ignore")
        base = f"{app_id or ''}{payload_text}{timestamp or ''}{app_secret}"
        expected_signature = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return expected_signature == signature_header

    @staticmethod
    def parse_message_events(channel_id: str, payload: dict[str, Any]) -> list[OmniChannelIncomingEvent]:
        """Normalize Zalo payload to canonical omnichannel events."""
        events: list[OmniChannelIncomingEvent] = []

        event_name = str(payload.get("event_name") or payload.get("event") or "").strip()
        sender_obj = payload.get("sender") or {}
        message_obj = payload.get("message") or {}

        sender_id = str(
            sender_obj.get("id")
            or sender_obj.get("user_id")
            or sender_obj.get("uid")
            or payload.get("fromuid")
            or ""
        ).strip()
        recipient_id = str(
            payload.get("oa_id")
            or (payload.get("recipient") or {}).get("id")
            or payload.get("appid")
            or ""
        ).strip()
        text = str(
            message_obj.get("text")
            or payload.get("content")
            or payload.get("message")
            or ""
        ).strip()

        if event_name and "text" not in event_name and not text:
            return events
        if not sender_id or not text:
            return events

        event: OmniChannelIncomingEvent = {
            "channel": "zalo_oa",
            "channel_id": channel_id,
            "external_account_id": recipient_id,
            "external_user_id": sender_id,
            "text": text,
            "raw_event": payload,
        }
        events.append(event)
        return events

