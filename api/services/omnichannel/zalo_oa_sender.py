"""Zalo OA outbound sender (ported from zca-bridge src/zalo-oa/sender.ts)."""

from __future__ import annotations

import logging
from typing import Any

from core.helper.ssrf_proxy import ssrf_proxy

logger = logging.getLogger(__name__)

MESSAGE_URL = "https://openapi.zalo.me/v3.0/oa/message/cs"
_IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "gif", "webp"})
_WINDOW_ERROR_CODES = frozenset({-32, -33, -2008})

_FILE_CONTENT_TYPE: dict[str, str] = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "txt": "text/plain",
    "zip": "application/zip",
}


class OaWindowError(ValueError):
    """Zalo OA consultation window closed or quota exceeded."""


class OaSendError(ValueError):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class ZaloFileRejectedError(ValueError):
    pass


def _file_content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _FILE_CONTENT_TYPE.get(ext, "application/octet-stream")


class ZaloOaSender:
    """Send text and attachments to Zalo OA users via the consultation (cs) API."""

    def __init__(self, access_token: str) -> None:
        self._access_token = (access_token or "").strip()

    def send_text(
        self,
        user_id: str,
        text: str,
        *,
        quote_message_id: str | None = None,
    ) -> str:
        recipient = {"user_id": user_id}
        qid = (quote_message_id or "").strip()
        if not qid:
            return self._send({"recipient": recipient, "message": {"text": text}})
        try:
            return self._send(
                {
                    "recipient": recipient,
                    "message": {"text": text, "quote_message_id": qid},
                }
            )
        except OaSendError:
            return self._send({"recipient": recipient, "message": {"text": text}})

    def send_attachment_from_url(
        self,
        user_id: str,
        *,
        attachment_url: str,
        attachment_type: str,
        caption: str = "",
    ) -> str:
        response = ssrf_proxy.get(attachment_url, timeout=(10, 60))
        response.raise_for_status()
        data = response.content
        if not data:
            raise ValueError("Attachment download returned empty body")
        filename = attachment_url.rsplit("/", 1)[-1].split("?")[0] or "file"
        if attachment_type == "image":
            return self.send_image_bytes(user_id, filename=filename, data=data, caption=caption)
        return self.send_file_bytes(user_id, filename=filename, data=data, caption=caption)

    def send_image_bytes(
        self,
        user_id: str,
        *,
        filename: str,
        data: bytes,
        caption: str = "",
    ) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        content_type = {
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "image/jpeg")
        attachment_id = self._upload(
            "https://openapi.zalo.me/v2.0/oa/upload/image",
            filename=filename,
            content_type=content_type,
            data=data,
            id_field="attachment_id",
            err_label="OA image upload failed",
        )
        return self._send(
            {
                "recipient": {"user_id": user_id},
                "message": {
                    "text": caption or None,
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "media",
                            "elements": [{"media_type": "image", "attachment_id": attachment_id}],
                        },
                    },
                },
            }
        )

    def send_request_user_info(
        self,
        user_id: str,
        *,
        title: str,
        subtitle: str,
        image_url: str,
    ) -> dict[str, object]:
        """Send request_user_info template card (zca-bridge requestInfoSender.ts)."""
        payload = {
            "recipient": {"user_id": user_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "request_user_info",
                        "elements": [{"title": title, "subtitle": subtitle, "image_url": image_url}],
                    },
                }
            },
        }
        try:
            self._send(payload)
            return {"ok": True, "code": 0, "message": ""}
        except OaSendError as e:
            return {"ok": False, "code": e.code if hasattr(e, "code") else -1, "message": str(e)}
        except OaWindowError as e:
            return {"ok": False, "code": -32, "message": str(e)}

    def send_file_bytes(
        self,
        user_id: str,
        *,
        filename: str,
        data: bytes,
        caption: str = "",
    ) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in _IMAGE_EXTS:
            return self.send_image_bytes(user_id, filename=filename, data=data, caption=caption)
        token = self._upload(
            "https://openapi.zalo.me/v2.0/oa/upload/file",
            filename=filename,
            content_type=_file_content_type(filename),
            data=data,
            id_field="token",
            err_label="OA file upload failed",
        )
        return self._send(
            {
                "recipient": {"user_id": user_id},
                "message": {
                    "text": caption or None,
                    "attachment": {"type": "file", "payload": {"token": token}},
                },
            }
        )

    def _upload(
        self,
        url: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        id_field: str,
        err_label: str,
    ) -> str:
        response = ssrf_proxy.post(
            url,
            params={"access_token": self._access_token},
            files={"file": (filename, data, content_type)},
            timeout=(10, 120),
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ZaloFileRejectedError(f"{err_label}: invalid response")
        inner = body.get("data")
        token = inner.get(id_field) if isinstance(inner, dict) else None
        if not token:
            err = f"{body.get('error', '')} {body.get('message', '')}".strip()
            raise ZaloFileRejectedError(f"{err_label}: {err}")
        return str(token)

    def _send(self, payload: dict[str, Any]) -> str:
        response = ssrf_proxy.post(
            MESSAGE_URL,
            params={"access_token": self._access_token},
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=(10, 30),
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise OaSendError(-1, "OA send failed: invalid response")
        code = int(body.get("error", -1))
        if code == 0:
            inner = body.get("data")
            msg_id = inner.get("message_id") if isinstance(inner, dict) else ""
            return str(msg_id or "")
        message = str(body.get("message") or "").strip()
        if code in _WINDOW_ERROR_CODES:
            raise OaWindowError(f"OA send blocked (window/quota): {code} {message}".strip())
        raise OaSendError(code, f"OA send failed: {code} {message}".strip())
