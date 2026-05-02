"""TikTok Business Messaging trigger endpoints for the omnichannel framework."""

from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, request

from controllers.trigger import bp
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_service import MessengerService
from tasks.omnichannel_tasks import process_meta_webhook_events

logger = logging.getLogger(__name__)


@bp.route("/tiktok/webhook/<string:channel_id>", methods=["GET"])
def verify_tiktok_webhook(channel_id: str):
    """Handle TikTok webhook verification for a specific channel.

    TikTok partners use different verification conventions across products,
    so we accept either `hub.challenge` style or fallback token checks.
    """
    channel_config = ChannelConfigService.get_meta_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "TikTok channel not found"}), 404

    challenge = request.args.get("hub.challenge") or request.args.get("challenge")
    if challenge:
        verify_token = request.args.get("hub.verify_token") or request.args.get("verify_token")
        if verify_token and verify_token != channel_config["verify_token"]:
            return jsonify({"error": "Invalid webhook verify token"}), 403
        return challenge, 200

    return jsonify({"ok": True}), 200


@bp.route("/tiktok/webhook/<string:channel_id>", methods=["POST"])
def ingest_tiktok_webhook(channel_id: str):
    """Receive TikTok webhook payloads and dispatch asynchronous processing."""
    channel_config = ChannelConfigService.get_meta_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "TikTok channel not found"}), 404

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    events = MessengerService.parse_message_events(channel_id=channel_id, payload=payload)
    process_meta_webhook_events.delay(channel_id, events, channel_config)

    logger.info(
        "TikTok webhook accepted channel=%s accepted_events=%s queued_async=%s",
        channel_id,
        len(events),
        True,
    )
    return jsonify({"ok": True, "accepted_events": len(events), "queued_async": True}), 200
