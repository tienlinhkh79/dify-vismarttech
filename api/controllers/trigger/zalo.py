"""Zalo OA trigger endpoints for the omnichannel framework."""

from __future__ import annotations

import logging
from typing import Any

from urllib.parse import quote

from flask import jsonify, redirect, request

from configs import dify_config
from controllers.trigger import bp
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.zalo_oauth_service import ZaloOAuthService
from services.omnichannel.zalo_service import ZaloService
from tasks.omnichannel_tasks import process_zalo_webhook_events

logger = logging.getLogger(__name__)


@bp.route("/zalo/oauth/callback", methods=["GET"])
def zalo_oauth_callback():
    """OAuth redirect target registered in Zalo Developer for OA token exchange."""
    base = dify_config.CONSOLE_WEB_URL.rstrip("/")
    err = request.args.get("error")
    if err:
        reason = request.args.get("error_description") or err
        return redirect(f"{base}/?zalo_oauth=error&reason={quote(str(reason), safe='')}")
    code = request.args.get("code")
    state = request.args.get("state")
    try:
        channel_id = ZaloOAuthService.handle_callback(code=code, state=state)
        return redirect(f"{base}/?zalo_oauth=success&channel_id={quote(channel_id, safe='')}")
    except ValueError:
        logger.warning("Zalo OAuth callback failed", exc_info=True)
        return redirect(f"{base}/?zalo_oauth=error&reason=invalid_callback")


@bp.route("/zalo/webhook/<string:channel_id>", methods=["GET"])
def verify_zalo_webhook(channel_id: str):
    """Handle optional Zalo verification handshake for a specific channel."""
    if not getattr(dify_config, "ZALO_TRIGGER_ENABLED", True):
        return jsonify({"error": "Zalo trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_zalo_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "Zalo channel not found"}), 404

    challenge = request.args.get("hub.challenge") or request.args.get("challenge")
    verify_token = request.args.get("hub.verify_token") or request.args.get("verify_token")
    if not challenge:
        return jsonify({"ok": True}), 200

    try:
        verified_challenge = ZaloService.verify_webhook_handshake(
            verify_token=verify_token,
            challenge=challenge,
            expected_token=channel_config["verify_token"],
        )
        return verified_challenge, 200
    except ValueError as e:
        logger.warning("Zalo handshake failed for channel %s: %s", channel_id, e)
        return jsonify({"error": str(e)}), 403


@bp.route("/zalo/webhook/<string:channel_id>", methods=["POST"])
def ingest_zalo_webhook(channel_id: str):
    """Receive Zalo events and normalize to omnichannel event payloads."""
    if not getattr(dify_config, "ZALO_TRIGGER_ENABLED", True):
        return jsonify({"error": "Zalo trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_zalo_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "Zalo channel not found"}), 404

    payload_bytes = request.get_data(cache=True)
    payload: dict[str, Any] = request.get_json(silent=True) or {}

    signature_header = request.headers.get("X-ZEvent-Signature")
    is_valid_signature = ZaloService.verify_event_signature(
        signature_header=signature_header,
        payload_bytes=payload_bytes,
        app_secret=channel_config["app_secret"],
        app_id=payload.get("app_id"),
        timestamp=payload.get("timestamp"),
    )
    if not is_valid_signature:
        return jsonify({"error": "Invalid webhook signature"}), 401

    events = ZaloService.parse_message_events(channel_id=channel_id, payload=payload)
    process_zalo_webhook_events.delay(channel_id, events, channel_config)
    logger.info(
        "Zalo webhook accepted channel=%s accepted_events=%s queued_async=%s",
        channel_id,
        len(events),
        True,
    )
    return jsonify({"ok": True, "accepted_events": len(events), "queued_async": True}), 200

