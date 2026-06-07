"""Zalo Personal inbound webhook from optional zca-js worker."""

from __future__ import annotations

import logging

from flask import jsonify, request

from configs import dify_config
from controllers.trigger import bp
from services.omnichannel.channel_config_service import ChannelConfigService
from tasks.omnichannel_tasks import process_zalo_personal_webhook_event

logger = logging.getLogger(__name__)


@bp.route("/zalo_personal/webhook/<string:channel_id>", methods=["POST"])
def zalo_personal_webhook(channel_id: str):
    if not getattr(dify_config, "ZALO_PERSONAL_TRIGGER_ENABLED", True):
        return jsonify({"error": "Zalo Personal trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_zalo_personal_channel_config(channel_id)
    if not channel_config:
        return jsonify({"error": "Channel not found"}), 404

    token_header = (request.headers.get("X-Omnichannel-Verify-Token") or "").strip()
    if token_header != channel_config["verify_token"]:
        return jsonify({"error": "Invalid verify token"}), 403

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Invalid payload"}), 400

    process_zalo_personal_webhook_event.delay(channel_id, body, channel_config)
    return jsonify({"ok": True}), 200
