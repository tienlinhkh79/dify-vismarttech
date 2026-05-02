"""Zalo OA adapter primitives for omnichannel webhook ingestion."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import hmac
import logging
import re
from secrets import compare_digest
from typing import Any, TypedDict

from services.omnichannel.messenger_service import OmniChannelIncomingEvent

logger = logging.getLogger(__name__)

# Only treat payloads as inbound user messages when Zalo labels them as such.
# OA-originated events (e.g. oa_send_*) and portal "webhook check" samples often
# include sender/message-like fields but must not require signature verification
# on the message path — otherwise Zalo's URL validation returns 401 incorrectly.
_ZALO_INBOUND_USER_MESSAGE_EVENT_PREFIXES: tuple[str, ...] = ("user_send_",)
_ZALO_INBOUND_USER_MESSAGE_EVENT_ALIASES: frozenset[str] = frozenset(
    {
        "anonymous_send_text",
        "anonymous_send_image",
        "anonymous_send_sticker",
        "anonymous_send_file",
        "anonymous_send_link",
        "anonymous_send_location",
        "anonymous_send_audio",
        "anonymous_send_video",
    }
)


class ZaloWebhookPayload(TypedDict, total=False):
    app_id: str
    timestamp: str | int


class ZaloService:
    """Service that validates and normalizes Zalo OA webhook data."""

    @staticmethod
    def _normalize_zevent_signature_header(value: str | None) -> str | None:
        """Strip optional mac= prefix / quotes; Zalo docs use hex digest in X-ZEvent-Signature."""
        if not value:
            return None
        s = value.strip()
        low = s.lower()
        if low.startswith("mac="):
            s = s[4:].strip()
        elif low.startswith("mac ="):
            s = s[5:].strip()
        if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
            s = s[1:-1].strip()
        s = re.sub(r"\s+", "", s)
        if not s:
            return None
        # e.g. "v1=<hex>" or "mac=<hex>"
        if "=" in s and not re.fullmatch(r"[0-9a-fA-F]+", s):
            _left, _right = s.split("=", 1)
            if _right:
                s = _right
        if re.fullmatch(r"[0-9a-fA-F]{64}", s):
            return s.lower()
        # Base64 digests must keep case
        return s or None

    @staticmethod
    def _payload_application_id(payload: dict[str, Any]) -> str:
        """Zalo MAC uses application ``appId``; do not treat ``oa_id`` as ``app_id``."""
        for key in ("app_id", "appId", "appid"):
            v = payload.get(key)
            if v is not None and str(v).strip():
                return str(v)
        return ""

    @staticmethod
    def _payload_oa_id(payload: dict[str, Any]) -> str:
        for key in ("oa_id", "oaId"):
            v = payload.get(key)
            if v is not None and str(v).strip():
                return str(v)
        return ""

    @staticmethod
    def _payload_timestamp(payload: dict[str, Any], header_timestamp: str | None) -> str:
        # Zalo OA examples use "timestamp"; some payloads use "timeStamp" (camelCase).
        for key in ("timestamp", "timeStamp"):
            v = payload.get(key)
            if v is not None and str(v).strip():
                return str(v)
        if header_timestamp and str(header_timestamp).strip():
            return str(header_timestamp).strip()
        return ""

    @staticmethod
    def _digest_matches_expected(expected_hex: str, sig_token: str) -> bool:
        """Compare Zalo header to SHA-256 hex digest, or to raw 32-byte digest encoded as Base64."""
        eh = expected_hex.lower()
        if len(eh) != 64:
            return False
        st = sig_token.strip()
        if len(st) == 64 and re.fullmatch(r"[0-9a-fA-F]{64}", st):
            return compare_digest(eh, st.lower())
        try:
            sig_bin = base64.b64decode(st, validate=True)
            exp_bin = bytes.fromhex(eh)
        except (ValueError, TypeError, binascii.Error):
            return False
        return len(sig_bin) == len(exp_bin) == 32 and compare_digest(exp_bin, sig_bin)

    @staticmethod
    def _sha256_concat_variants(app_id: str, body: str, ts: str, secret: str) -> list[str]:
        """Common permutations seen in Zalo / integrator docs (app_id + body + ts + secret canonical form)."""
        a, b, t, s = app_id, body, ts, secret
        return [
            f"{a}{b}{t}{s}",
            f"{b}{a}{t}{s}",
            f"{a}{t}{b}{s}",
            f"{t}{a}{b}{s}",
            f"{b}{t}{a}{s}",
            f"{t}{b}{a}{s}",
        ]

    @staticmethod
    def _mini_app_style_sorted_values_hex(data: dict[str, Any], api_key: str) -> str:
        """Zalo Mini App / Open API doc: sort keys A–Z, concat values (objects JSON), sha256(content + key)."""
        keys = sorted(data.keys())
        parts: list[str] = []
        for k in keys:
            v = data[k]
            if isinstance(v, (dict, list)):
                parts.append(json.dumps(v, separators=(",", ":"), ensure_ascii=False, sort_keys=True))
            elif isinstance(v, bool):
                parts.append("true" if v else "false")
            elif v is None:
                parts.append("null")
            else:
                parts.append(str(v))
        content = "".join(parts)
        return hashlib.sha256(f"{content}{api_key}".encode("utf-8")).hexdigest()

    @staticmethod
    def _body_segments_for_mac(payload: dict[str, Any], payload_text: str) -> list[str]:
        """Segments used as ``data`` in mac = sha256(appId + data + timeStamp + OAsecret_key)."""
        segments: list[str] = []
        if payload_text:
            segments.append(payload_text)
        try:
            canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            canon = ""
        if canon and canon not in segments:
            segments.append(canon)
        raw_data = payload.get("data")
        if raw_data is not None:
            if isinstance(raw_data, str) and raw_data not in segments:
                segments.append(raw_data)
            elif isinstance(raw_data, (dict, list)):
                try:
                    inner = json.dumps(raw_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                except (TypeError, ValueError):
                    inner = ""
                if inner and inner not in segments:
                    segments.append(inner)
        return segments

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
        payload: dict[str, Any],
        *,
        fallback_app_id: str = "",
        fallback_oa_id: str = "",
        header_timestamp: str | None = None,
    ) -> bool:
        """Validate Zalo OA webhook MAC per Zalo docs: mac = sha256(app_id + data + timeStamp + OAsecret_key).

        ``data`` is the raw JSON body (UTF-8) as sent by Zalo. ``app_id`` / ``timeStamp`` are taken from JSON
        (aliases supported); if the URL-check POST omits ``app_id`` in the body, pass ``fallback_app_id`` from
        the channel row. ``fallback_oa_id`` (``page_id`` / OA id) is tried when Zalo signs with OA id instead of
        application id. If ``timeStamp`` is only in a header, pass ``header_timestamp``.
        """
        if not signature_header:
            # Some sandbox integrations forward events without signature.
            return True
        app_secret = (app_secret or "").replace("\ufeff", "").strip()
        if not app_secret:
            return False

        normalized = ZaloService._normalize_zevent_signature_header(signature_header)
        if not normalized:
            return False

        payload_text = payload_bytes.decode("utf-8", errors="ignore")
        if payload_text.startswith("\ufeff"):
            payload_text = payload_text[1:]

        app_from_body = ZaloService._payload_application_id(payload)
        oa_from_body = ZaloService._payload_oa_id(payload)
        ts_from_body = ZaloService._payload_timestamp(payload, None)
        ts_from_header = ZaloService._payload_timestamp({}, header_timestamp)

        # Prefer application id from JSON, then configured app id, then OA ids (some probes omit app_id in body).
        app_candidates: list[str] = []

        def _add_app_candidate(value: str) -> None:
            v = (value or "").strip()
            if v and v not in app_candidates:
                app_candidates.append(v)

        _add_app_candidate(app_from_body)
        _add_app_candidate(fallback_app_id)
        _add_app_candidate(oa_from_body)
        _add_app_candidate(fallback_oa_id)
        if not app_candidates:
            app_candidates.append("")

        ts_candidates: list[str] = []
        if ts_from_body:
            ts_candidates.append(ts_from_body)
        if ts_from_header and ts_from_header not in ts_candidates:
            ts_candidates.append(ts_from_header)
        if not ts_candidates:
            ts_candidates.append("")

        secret_b = app_secret.encode("utf-8")
        hmac_body_hex = hmac.new(secret_b, payload_bytes, hashlib.sha256).hexdigest()
        if ZaloService._digest_matches_expected(hmac_body_hex, normalized):
            return True

        mini_hex = ZaloService._mini_app_style_sorted_values_hex(payload, app_secret)
        if ZaloService._digest_matches_expected(mini_hex, normalized):
            return True

        body_segments = ZaloService._body_segments_for_mac(payload, payload_text)
        for body_seg in body_segments:
            seg_bytes = body_seg.encode("utf-8")
            hmac_seg_hex = hmac.new(secret_b, seg_bytes, hashlib.sha256).hexdigest()
            if ZaloService._digest_matches_expected(hmac_seg_hex, normalized):
                return True

        for app_id in app_candidates:
            for timestamp in ts_candidates:
                pre = f"{app_id}{timestamp}".encode("utf-8")
                hmac_pre_body_hex = hmac.new(secret_b, pre + payload_bytes, hashlib.sha256).hexdigest()
                if ZaloService._digest_matches_expected(hmac_pre_body_hex, normalized):
                    return True
                for body_seg in body_segments:
                    seg_bytes = body_seg.encode("utf-8")
                    hmac_pre_seg = hmac.new(secret_b, pre + seg_bytes, hashlib.sha256).hexdigest()
                    if ZaloService._digest_matches_expected(hmac_pre_seg, normalized):
                        return True
                    for base in ZaloService._sha256_concat_variants(app_id, body_seg, timestamp, app_secret):
                        expected_hex = hashlib.sha256(base.encode("utf-8")).hexdigest()
                        if ZaloService._digest_matches_expected(expected_hex, normalized):
                            return True

        logger.warning(
            "Zalo webhook MAC mismatch. Ensure client_secret is the OA Secret Key from Zalo Developer "
            "(Webhook section), not the Application Secret Key, unless they match. body_has_app_id=%s body_has_ts=%s",
            bool(app_from_body or oa_from_body),
            bool(ts_from_body),
        )
        return False

    @staticmethod
    def _is_zalo_inbound_user_message_event(event_name: str) -> bool:
        en = (event_name or "").strip().lower()
        if not en:
            return False
        if en in _ZALO_INBOUND_USER_MESSAGE_EVENT_ALIASES:
            return True
        return any(en.startswith(p) for p in _ZALO_INBOUND_USER_MESSAGE_EVENT_PREFIXES)

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

        named_inbound = bool(event_name) and ZaloService._is_zalo_inbound_user_message_event(event_name)
        legacy_unnamed_inbound = not event_name and bool(sender_id and text)
        if event_name and not named_inbound:
            return events
        if not event_name and not legacy_unnamed_inbound:
            return events

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

