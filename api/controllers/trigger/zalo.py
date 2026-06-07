"""Zalo OA trigger endpoints for the omnichannel framework."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from flask import Response, jsonify, redirect, request

from configs import dify_config
from controllers.trigger import bp
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.zalo_bridge_dispatch_service import ZaloBridgeDispatchService
from services.omnichannel.zalo_media_archive_service import ZaloMediaArchiveService
from services.omnichannel.zalo_oauth_service import ZaloOAuthCallbackError, ZaloOAuthService
from services.omnichannel.zalo_service import ZaloService
from tasks.omnichannel_tasks import process_zalo_bridge_worker

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
    except ZaloOAuthCallbackError as e:
        logger.warning("Zalo OAuth callback failed reason=%s", e.reason, exc_info=True)
        return redirect(f"{base}/?zalo_oauth=error&reason={quote(e.reason, safe='')}")
    except ValueError:
        logger.warning("Zalo OAuth callback failed", exc_info=True)
        return redirect(f"{base}/?zalo_oauth=error&reason=oauth_callback_error")


@bp.route("/zalo/media/<path:token>", methods=["GET"])
def serve_zalo_archived_media(token: str):
    """Serve archived Zalo media via signed token (zca-bridge /media parity)."""
    loaded = ZaloMediaArchiveService.load_bytes(token)
    if not loaded:
        return jsonify({"error": "Media not found"}), 404
    data, content_type = loaded
    return Response(data, mimetype=content_type)


@bp.route("/zalo/webhook/<string:channel_id>", methods=["GET"])
def verify_zalo_webhook(channel_id: str):
    """Handle optional Zalo verification handshake for a specific channel."""
    if not getattr(dify_config, "ZALO_TRIGGER_ENABLED", True):
        return jsonify({"error": "Zalo trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_zalo_channel_config(channel_id, skip_oauth_refresh=True)
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
    """Receive Zalo OA events, verify MAC, enqueue durable bridge jobs."""
    if not getattr(dify_config, "ZALO_TRIGGER_ENABLED", True):
        return jsonify({"error": "Zalo trigger is disabled"}), 404

    channel_config = ChannelConfigService.get_zalo_channel_config(channel_id, skip_oauth_refresh=True)
    if not channel_config:
        return jsonify({"error": "Zalo channel not found"}), 404

    payload_bytes = request.get_data(cache=True)
    payload: dict[str, Any] = request.get_json(silent=True) or {}
    event_name = str(payload.get("event_name") or payload.get("event") or "").strip()

    signature_header = request.headers.get("X-ZEvent-Signature")
    header_ts = request.headers.get("X-ZEvent-Timestamp")

    is_message_event = bool(ZaloService.parse_webhook_event(channel_id, payload)) or event_name == "user_submit_info"
    if is_message_event:
        is_valid_signature = ZaloService.verify_event_signature(
            signature_header=signature_header,
            payload_bytes=payload_bytes,
            app_secret=channel_config["app_secret"],
            payload=payload,
            fallback_app_id=str(channel_config.get("zalo_application_id") or ""),
            fallback_oa_id=str(channel_config.get("oa_id") or ""),
            header_timestamp=header_ts,
        )
        if not is_valid_signature:
            return jsonify({"error": "Invalid webhook signature"}), 401
    elif signature_header:
        is_valid_probe_sig = ZaloService.verify_event_signature(
            signature_header=signature_header,
            payload_bytes=payload_bytes,
            app_secret=channel_config["app_secret"],
            payload=payload,
            fallback_app_id=str(channel_config.get("zalo_application_id") or ""),
            fallback_oa_id=str(channel_config.get("oa_id") or ""),
            header_timestamp=header_ts,
        )
        if not is_valid_probe_sig:
            logger.warning(
                "Zalo webhook probe signature mismatch but accepted for setup channel=%s payload_keys=%s",
                channel_id,
                sorted(payload.keys())[:12],
            )
        return jsonify({"ok": True, "accepted_events": 0, "queued_async": False}), 200

    if not is_message_event:
        return jsonify({"ok": True, "accepted_events": 0, "queued_async": False, "ignored": event_name or True}), 200

    enqueued = ZaloBridgeDispatchService.enqueue_webhook(channel_id=channel_id, payload=payload)
    queued_async = False
    if enqueued:
        try:
            process_zalo_bridge_worker.delay()
            queued_async = True
        except Exception:
            logger.exception("Zalo bridge Celery enqueue failed, processing inline channel=%s", channel_id)
            ZaloBridgeDispatchService.run_worker_tick(max_jobs=5)

    logger.info(
        "Zalo webhook accepted channel=%s event=%s enqueued=%s queued_async=%s",
        channel_id,
        event_name,
        enqueued,
        queued_async,
    )
    return jsonify({"ok": True, "accepted_events": 1 if enqueued else 0, "queued_async": queued_async}), 200
