"""Facebook Messenger trigger endpoints for the omnichannel framework."""

from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, request

from configs import dify_config
from controllers.trigger import bp
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.messenger_service import MessengerService

logger = logging.getLogger(__name__)


@bp.route("/messenger/webhook/<string:channel_id>", methods=["GET"])
def verify_messenger_webhook(channel_id: str):
    """Handle Messenger verification handshake for a specific channel."""
    # Backward-compatible guard: older runtime images may not expose this flag yet.
    if not getattr(dify_config, "MESSENGER_TRIGGER_ENABLED", True):
        return jsonify({"error": "Messenger trigger is disabled"}), 404
    channel_config = ChannelConfigService.get_messenger_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "Messenger channel not found"}), 404

    try:
        challenge = MessengerService.verify_webhook_handshake(
            mode=request.args.get("hub.mode"),
            verify_token=request.args.get("hub.verify_token"),
            challenge=request.args.get("hub.challenge"),
            expected_token=channel_config["verify_token"],
        )
        return challenge, 200
    except ValueError as e:
        logger.warning("Messenger handshake failed for channel %s: %s", channel_id, e)
        return jsonify({"error": str(e)}), 403


@bp.route("/messenger/webhook/<string:channel_id>", methods=["POST"])
def ingest_messenger_webhook(channel_id: str):
    """Receive Messenger events and normalize to omnichannel event payloads."""
    # Backward-compatible guard: older runtime images may not expose this flag yet.
    if not getattr(dify_config, "MESSENGER_TRIGGER_ENABLED", True):
        return jsonify({"error": "Messenger trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_messenger_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "Messenger channel not found"}), 404

    # Keep body cached so we can both verify signature and parse JSON payload.
    payload_bytes = request.get_data(cache=True)
    signature_header = request.headers.get("X-Hub-Signature-256")
    is_valid_signature = MessengerService.verify_payload_signature(
        signature_header=signature_header,
        payload=payload_bytes,
        app_secret=channel_config["app_secret"],
    )
    if not is_valid_signature:
        return jsonify({"error": "Invalid webhook signature"}), 401

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        entry_count = len(payload.get("entry", []))
    except Exception:
        entry_count = 0

    # Keep payload logging lightweight to avoid exposing sensitive data.
    logger.info("Messenger webhook received channel=%s entry_count=%s", channel_id, entry_count)

    events = MessengerService.parse_message_events(channel_id=channel_id, payload=payload)
    if not events:
        messaging_event_types: list[str] = []
        for entry in payload.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message"):
                    message_payload = messaging_event.get("message") or {}
                    if isinstance(message_payload, dict):
                        if "text" in message_payload:
                            messaging_event_types.append("message:text")
                        elif "attachments" in message_payload:
                            messaging_event_types.append("message:attachments")
                        else:
                            messaging_event_types.append("message:other")
                elif messaging_event.get("postback"):
                    messaging_event_types.append("postback")
                elif messaging_event.get("delivery"):
                    messaging_event_types.append("delivery")
                elif messaging_event.get("read"):
                    messaging_event_types.append("read")
                else:
                    messaging_event_types.append("unknown")

        logger.info(
            "Messenger webhook parsed no text events channel=%s event_types=%s",
            channel_id,
            messaging_event_types,
        )

    sent_replies = MessengerRuntimeService.process_events(
        channel_id=channel_id,
        events=events,
        channel_config=channel_config,
    )
    logger.info(
        "Messenger webhook processed channel=%s accepted_events=%s sent_replies=%s",
        channel_id,
        len(events),
        sent_replies,
    )
    return jsonify({"ok": True, "accepted_events": len(events), "sent_replies": sent_replies}), 200

