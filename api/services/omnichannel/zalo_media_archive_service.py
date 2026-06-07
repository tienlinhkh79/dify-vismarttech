"""Durable Zalo media archive with tokenized URLs (ported from zca-bridge src/media/archive.ts)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from typing import TypedDict
from urllib.parse import quote

from configs import dify_config
from core.helper.ssrf_proxy import ssrf_proxy
from extensions.ext_storage import storage

logger = logging.getLogger(__name__)

_ARCHIVE_PREFIX = "omnichannel/zalo-media/"
_TOKEN_SEP = "."


class ArchivedMedia(TypedDict):
    key: str
    content_type: str
    size: int


class ZaloMediaArchiveService:
    @staticmethod
    def _storage_key(key: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_./-]", "_", key).strip("/")
        return f"{_ARCHIVE_PREFIX}{safe}"

    @staticmethod
    def _meta_storage_key(data_key: str) -> str:
        return f"{data_key}.meta"

    @classmethod
    def put(cls, key: str, data: bytes, content_type: str) -> None:
        data_key = cls._storage_key(key)
        meta_key = cls._meta_storage_key(data_key)
        storage.save(data_key, data)
        storage.save(meta_key, (content_type or "application/octet-stream").encode("utf-8"))

    @classmethod
    def get(cls, token: str) -> ArchivedMedia | None:
        key = cls._verify_token(token)
        if not key:
            return None
        data_key = cls._storage_key(key)
        meta_key = cls._meta_storage_key(data_key)
        try:
            if not storage.exists(data_key):
                return None
            data = storage.load(data_key)
            content_type = "application/octet-stream"
            if storage.exists(meta_key):
                content_type = storage.load(meta_key).decode("utf-8", errors="ignore").strip() or content_type
            return {"key": key, "content_type": content_type, "size": len(data)}
        except Exception:
            logger.debug("Zalo media archive read failed key=%s", key, exc_info=True)
            return None

    @classmethod
    def load_bytes(cls, token: str) -> tuple[bytes, str] | None:
        key = cls._verify_token(token)
        if not key:
            return None
        data_key = cls._storage_key(key)
        meta_key = cls._meta_storage_key(data_key)
        try:
            data = storage.load(data_key)
            content_type = "application/octet-stream"
            if storage.exists(meta_key):
                content_type = storage.load(meta_key).decode("utf-8", errors="ignore").strip() or content_type
            return data, content_type
        except Exception:
            return None

    @classmethod
    def url_for(cls, key: str) -> str:
        token = cls._sign_token(key)
        base = dify_config.TRIGGER_URL.rstrip("/")
        return f"{base}/triggers/zalo/media/{quote(token, safe='')}"

    @classmethod
    def _sign_token(cls, key: str) -> str:
        secret = (dify_config.SECRET_KEY or "dify").encode("utf-8")
        exp = int(time.time()) + 86400 * 365 * 10
        payload = f"{key}{_TOKEN_SEP}{exp}"
        sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}{_TOKEN_SEP}{sig}"

    @classmethod
    def _verify_token(cls, token: str) -> str | None:
        parts = (token or "").split(_TOKEN_SEP)
        if len(parts) != 3:
            return None
        key, exp_s, sig = parts
        secret = (dify_config.SECRET_KEY or "dify").encode("utf-8")
        payload = f"{key}{_TOKEN_SEP}{exp_s}"
        expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        try:
            if int(exp_s) < int(time.time()):
                return None
        except ValueError:
            return None
        return key

    @classmethod
    def download_and_archive(
        cls,
        *,
        channel_id: str,
        thread_id: str,
        msg_id: str,
        href: str,
        filename: str,
        media_type: str,
    ) -> str | None:
        """Download Zalo CDN media, archive locally, return public token URL."""
        try:
            target = href
            response = ssrf_proxy.get(target, timeout=(10, 60), follow_redirects=True)
            if response.status_code >= 400:
                return None
            data = response.content
            if not data:
                return None
            content_type = (response.headers.get("content-type") or "application/octet-stream").split(";")[0]
            safe_name = re.sub(r"[^\w.\-]", "_", filename or "file")[:120] or "file"
            key = f"{channel_id}/{thread_id}/{msg_id}_{safe_name}"
            cls.put(key, data, content_type)
            return cls.url_for(key)
        except Exception:
            logger.warning("Zalo media archive failed href=%s", href, exc_info=True)
            return None
