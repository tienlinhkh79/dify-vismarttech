"""Zalo personal account QR login via optional zca-js worker (zca-bridge src/zalo/qrLoginService.ts)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from configs import dify_config
from services.omnichannel.channel_config_service import ChannelConfigService

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
    def ensure_worker_webhook(cls, channel_id: str) -> None:
        """Re-register inbound webhook on worker after restarts (best-effort)."""
        cfg = ChannelConfigService.get_zalo_personal_channel_config(channel_id, require_enabled=False)
        if not cfg:
            return
        cls.notify_worker_webhook(channel_id, verify_token=cfg["verify_token"])

    @classmethod
    def get_login_status(cls, channel_id: str) -> dict[str, Any]:
        base = cls._worker_base()
        if not base:
            return {
                "status": "worker_unconfigured",
                "connected": False,
                "scanned_display_name": "",
                "error": "",
            }
        try:
            response = cls._worker_request(
                "GET",
                f"/channels/{channel_id}/login/status",
                timeout=(5, 10),
            )
            if response.status_code == 404:
                return {
                    "status": "pending_qr",
                    "connected": False,
                    "scanned_display_name": "",
                    "error": "",
                }
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict):
                status = str(body.get("status") or "pending_qr")
                connected = bool(body.get("connected")) or status == "connected"
                if connected:
                    cls.ensure_worker_webhook(channel_id)
                return {
                    "status": status,
                    "connected": connected,
                    "scanned_display_name": str(body.get("scanned_display_name") or ""),
                    "error": str(body.get("error") or ""),
                }
        except Exception:
            logger.debug("Zalo personal status check failed channel=%s", channel_id, exc_info=True)
        return {
            "status": "worker_unreachable",
            "connected": False,
            "scanned_display_name": "",
            "error": "",
        }

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
    def mark_seen(cls, *, channel_id: str, message_meta: dict[str, Any]) -> None:
        """Best-effort: mark inbound message as seen via zca-js sendSeenEvent."""
        base = cls._worker_base()
        if not base or not message_meta:
            return
        try:
            cls._worker_request(
                "POST",
                f"/channels/{channel_id}/presence/seen",
                json={"message": message_meta},
                timeout=(5, 10),
            )
        except Exception:
            logger.debug("Zalo personal mark_seen failed channel=%s", channel_id, exc_info=True)

    @classmethod
    def send_typing(cls, *, channel_id: str, thread_id: str) -> None:
        """Best-effort: show typing indicator (three dots) via zca-js sendTypingEvent."""
        base = cls._worker_base()
        if not base:
            return
        thread = (thread_id or "").strip()
        if not thread:
            return
        try:
            cls._worker_request(
                "POST",
                f"/channels/{channel_id}/presence/typing",
                json={"thread_id": thread},
                timeout=(5, 10),
            )
        except Exception:
            logger.debug("Zalo personal send_typing failed channel=%s", channel_id, exc_info=True)

    @classmethod
    def send_text_message(cls, *, channel_id: str, thread_id: str, text: str) -> dict[str, Any]:
        return cls.send_rich_message(channel_id=channel_id, thread_id=thread_id, text=text)

    @classmethod
    def send_rich_message(
        cls,
        *,
        channel_id: str,
        thread_id: str,
        text: str,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        base = cls._worker_base()
        if not base:
            raise ValueError(
                "Unable to send Zalo Personal messages. Please try again later or contact your administrator."
            )
        body_text = (text or "").strip()
        images = [url.strip() for url in (image_urls or []) if isinstance(url, str) and url.strip()]
        if not body_text and not images:
            raise ValueError("Message text or image_urls is required")
        thread = (thread_id or "").strip()
        if not thread:
            raise ValueError("Recipient is missing")
        for url in images:
            if not url.lower().startswith("https://"):
                raise ValueError("image_urls must use https")
        response = cls._worker_request(
            "POST",
            f"/channels/{channel_id}/messages/send",
            json={
                "thread_id": thread,
                "text": body_text,
                "image_urls": images,
            },
            timeout=(5, 60),
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
