"""Helpers for Meta CDN URLs that browsers cannot load from our origin (403)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

_META_CDN_HOST_MARKERS = (
    "fbcdn.net",
    "fbsbx.com",
    "facebook.com",
    "fb.com",
)


def is_meta_cdn_url(url: str | None) -> bool:
    value = (url or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").lower()
    except ValueError:
        host = ""
    if host and any(marker in host for marker in _META_CDN_HOST_MARKERS):
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in _META_CDN_HOST_MARKERS)


def sanitize_browser_image_url(url: str | None) -> str | None:
    """Return None for Meta CDN URLs so the UI never attempts to load them."""
    value = (url or "").strip()
    if not value or is_meta_cdn_url(value):
        return None
    return value


def sanitize_attachment_list(attachments: Any) -> list[Any]:
    if not isinstance(attachments, list):
        return []
    cleaned: list[Any] = []
    for item in attachments:
        if not isinstance(item, dict):
            cleaned.append(item)
            continue
        url = item.get("url")
        if isinstance(url, str) and is_meta_cdn_url(url):
            next_item = dict(item)
            next_item["url"] = None
            next_item["meta_cdn_blocked"] = True
            cleaned.append(next_item)
        else:
            cleaned.append(item)
    return cleaned
