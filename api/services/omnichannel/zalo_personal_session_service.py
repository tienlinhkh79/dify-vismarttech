"""Zalo personal account QR login via optional zca-js worker (zca-bridge src/zalo/qrLoginService.ts)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from configs import dify_config

logger = logging.getLogger(__name__)


class ZaloPersonalSessionService:
    @staticmethod
    def _worker_base() -> str:
        return (dify_config.ZALO_PERSONAL_WORKER_URL or "").rstrip("/")

    @classmethod
    def _worker_request(cls, method: str, path: str, **kwargs: Any) -> httpx.Response:
        base = cls._worker_base()
        if not base:
            raise ValueError(
                "Unable to reach Zalo Personal worker. Please try again later or contact your administrator."
            )
        url = f"{base}{path}"
        timeout = kwargs.pop("timeout", (5, 30))
        httpx_timeout = httpx.Timeout(
            connect=timeout[0], read=timeout[1], write=timeout[1], pool=timeout[0]
        )
        with httpx.Client(timeout=httpx_timeout) as client:
            return client.request(method, url, **kwargs)

    @classmethod
    def trigger_webhook_url(cls, channel_id: str) -> str:
        base = (dify_config.TRIGGER_URL or "http://localhost:5001").rstrip("/")
        return f"{base}/triggers/zalo_personal/webhook/{channel_id}"

    @classmethod
    def get_login_status(cls, channel_id: str) -> str:
        base = cls._worker_base()
        if not base:
            return "worker_unconfigured"
        try:
            response = cls._worker_request(
                "GET",
                f"/channels/{channel_id}/login/status",
                timeout=(5, 10),
            )
            if response.status_code == 404:
                return "pending_qr"
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict):
                return str(body.get("status") or "pending_qr")
        except Exception:
            logger.debug("Zalo personal status check failed channel=%s", channel_id, exc_info=True)
        return "worker_unreachable"

    @classmethod
    def start_login(cls, channel_id: str) -> dict[str, Any]:
        base = cls._worker_base()
        if not base:
            raise ValueError(
                "Unable to start Zalo Personal login. Please try again later or contact your administrator."
            )
        response = cls._worker_request(
            "POST",
            f"/channels/{channel_id}/login/start",
            json={},
            timeout=(10, 120),
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Invalid response from Zalo personal worker")
        qr = str(body.get("qr_data_uri") or body.get("qrImageBase64") or "").strip()
        if qr and not qr.startswith("data:"):
            qr = f"data:image/png;base64,{qr}"
        return {
            "qr_data_uri": qr,
            "status": str(body.get("status") or "pending_qr"),
        }

    @classmethod
    def send_text_message(cls, *, channel_id: str, thread_id: str, text: str) -> dict[str, Any]:
        base = cls._worker_base()
        if not base:
            raise ValueError(
                "Unable to send Zalo Personal messages. Please try again later or contact your administrator."
            )
        body_text = (text or "").strip()
        if not body_text:
            raise ValueError("Message text is required")
        thread = (thread_id or "").strip()
        if not thread:
            raise ValueError("Recipient is missing")
        response = cls._worker_request(
            "POST",
            f"/channels/{channel_id}/messages/send",
            json={"thread_id": thread, "text": body_text},
            timeout=(5, 30),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Invalid response from Zalo personal worker")
        return payload

    @classmethod
    def notify_worker_webhook(cls, channel_id: str, *, verify_token: str) -> None:
        """Best-effort: tell worker where to POST inbound events."""
        base = cls._worker_base()
        if not base:
            return
        try:
            cls._worker_request(
                "POST",
                f"/channels/{channel_id}/webhook/configure",
                json={
                    "webhook_url": cls.trigger_webhook_url(channel_id),
                    "verify_token": verify_token,
                },
                timeout=(5, 10),
            )
        except Exception:
            logger.debug("Zalo personal worker webhook configure failed channel=%s", channel_id, exc_info=True)
