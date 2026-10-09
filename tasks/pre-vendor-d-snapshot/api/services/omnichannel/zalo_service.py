"""Zalo OA adapter primitives for omnichannel webhook ingestion."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from secrets import compare_digest
from typing import Any

from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.zalo_oa_classify import (
    ZaloOaWebhookEvent,
    classify_oa_webhook_event,
    is_self_oa_event,
    should_enqueue_oa_webhook,
)

logger = logging.getLogger(__name__)


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
        if "=" in s and not re.fullmatch(r"[0-9a-fA-F]+", s):
            _left, _right = s.split("=", 1)
            if _right:
                s = _right
        if re.fullmatch(r"[0-9a-fA-F]{64}", s):
            return s.lower()
        return s or None

    @staticmethod
    def _payload_application_id(payload: dict[str, Any]) -> str:
        for key in ("app_id", "appId", "appid"):
            v = payload.get(key)
            if v is not None and str(v).strip():
                return str(v)
        return ""

    @staticmethod
    def _payload_timestamp(payload: dict[str, Any], header_timestamp: str | None) -> str:
        for key in ("timestamp", "timeStamp"):
            v = payload.get(key)
            if v is not None and str(v).strip():
                return str(v)
        if header_timestamp and str(header_timestamp).strip():
            return str(header_timestamp).strip()
        return ""

    @staticmethod
    def compute_documented_mac(*, app_id: str, raw_body: str, timestamp: str, oa_secret_key: str) -> str:
        """Canonical Zalo OA MAC: sha256(appId + rawBody + timestamp + oaSecretKey)."""
        base = f"{app_id}{raw_body}{timestamp}{oa_secret_key}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_webhook_handshake(
        verify_token: str | None,
        challenge: str | None,
        expected_token: str,
    ) -> str:
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
        """Validate Zalo OA webhook MAC; primary path matches zca-bridge verify.ts."""
        if not signature_header:
            return True
        app_secret = (app_secret or "").replace("\ufeff", "").strip()
        if not app_secret:
            return False

        normalized = ZaloService._normalize_zevent_signature_header(signature_header)
        if not normalized:
            return False

        payload_text = payload_bytes.decode("utf-8", errors="ignore")
        payload_text = payload_text.removeprefix("\ufeff")

        app_id = ZaloService._payload_application_id(payload) or (fallback_app_id or "").strip()
        if not app_id and fallback_oa_id:
            app_id = fallback_oa_id.strip()
        timestamp = ZaloService._payload_timestamp(payload, header_timestamp)

        documented = ZaloService.compute_documented_mac(
            app_id=app_id,
            raw_body=payload_text,
            timestamp=timestamp,
            oa_secret_key=app_secret,
        )
        if compare_digest(documented, normalized.lower()):
            return True

        return ZaloService._verify_legacy_signature_variants(
            normalized=normalized,
            payload_bytes=payload_bytes,
            payload=payload,
            payload_text=payload_text,
            app_secret=app_secret,
            fallback_app_id=fallback_app_id,
            fallback_oa_id=fallback_oa_id,
            header_timestamp=header_timestamp,
        )

    @staticmethod
    def _verify_legacy_signature_variants(
        *,
        normalized: str,
        payload_bytes: bytes,
        payload: dict[str, Any],
        payload_text: str,
        app_secret: str,
        fallback_app_id: str,
        fallback_oa_id: str,
        header_timestamp: str | None,
    ) -> bool:
        """Fallback MAC shapes kept for older Zalo portal probes and integrator docs."""
        secret_b = app_secret.encode("utf-8")
        hmac_body_hex = hmac.new(secret_b, payload_bytes, hashlib.sha256).hexdigest()
        if compare_digest(hmac_body_hex, normalized.lower()):
            return True

        app_from_body = ZaloService._payload_application_id(payload)
        oa_from_body = str(payload.get("oa_id") or payload.get("oaId") or "").strip()
        ts_from_body = ZaloService._payload_timestamp(payload, None)
        ts_from_header = ZaloService._payload_timestamp({}, header_timestamp)

        app_candidates: list[str] = []
        for value in (app_from_body, fallback_app_id, oa_from_body, fallback_oa_id):
            v = (value or "").strip()
            if v and v not in app_candidates:
                app_candidates.append(v)
        if not app_candidates:
            app_candidates.append("")

        ts_candidates: list[str] = []
        for value in (ts_from_body, ts_from_header):
            v = (value or "").strip()
            if v and v not in ts_candidates:
                ts_candidates.append(v)
        if not ts_candidates:
            ts_candidates.append("")

        for candidate_app_id in app_candidates:
            for candidate_ts in ts_candidates:
                legacy = ZaloService.compute_documented_mac(
                    app_id=candidate_app_id,
                    raw_body=payload_text,
                    timestamp=candidate_ts,
                    oa_secret_key=app_secret,
                )
                if compare_digest(legacy, normalized.lower()):
                    return True

        inner = payload.get("data")
        if isinstance(inner, (dict, list, str)):
            inner_text = inner if isinstance(inner, str) else json.dumps(inner, separators=(",", ":"))
            for candidate_app_id in app_candidates:
                for candidate_ts in ts_candidates:
                    legacy = ZaloService.compute_documented_mac(
                        app_id=candidate_app_id,
                        raw_body=inner_text,
                        timestamp=candidate_ts,
                        oa_secret_key=app_secret,
                    )
                    if compare_digest(legacy, normalized.lower()):
                        return True

        logger.warning(
            "Zalo webhook MAC mismatch. Ensure client_secret is the OA Secret Key from Zalo Developer "
            "(Webhook section), and zalo_application_id matches the Zalo app id used for signing."
        )
        return False

    @staticmethod
    def parse_webhook_event(channel_id: str, payload: dict[str, Any]) -> ZaloOaWebhookEvent | None:
        """Classify one Zalo OA webhook body using zca-bridge rules."""
        event_name = str(payload.get("event_name") or payload.get("event") or "").strip()
        if not should_enqueue_oa_webhook(event_name):
            return None
        return classify_oa_webhook_event(channel_id, payload, is_self=is_self_oa_event(event_name))

    @staticmethod
    def parse_message_events(channel_id: str, payload: dict[str, Any]) -> list[OmniChannelIncomingEvent]:
        """Normalize Zalo payload to canonical omnichannel events (0 or 1 item)."""
        event = ZaloService.parse_webhook_event(channel_id, payload)
        if not event:
            return []
        return [event]
