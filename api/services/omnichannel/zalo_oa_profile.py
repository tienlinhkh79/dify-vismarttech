"""Fetch Zalo Official Account display fields from Zalo Open API (name, avatar)."""

from __future__ import annotations

import logging

from core.helper.ssrf_proxy import ssrf_proxy

logger = logging.getLogger(__name__)


def fetch_zalo_oa_display(*, access_token: str) -> dict[str, str]:
    """Resolve OA access token to display name and avatar URL (best-effort)."""
    token = (access_token or "").strip()
    name = ""
    avatar = ""
    if not token:
        return {"name": name, "avatar_url": avatar}
    url = "https://openapi.zalo.me/v2.0/oa/getoa"
    try:
        response = ssrf_proxy.get(
            url,
            params={"access_token": token},
            timeout=(5, 15),
        )
        if response.status_code >= 400:
            return {"name": name, "avatar_url": avatar}
        data = response.json()
        if not isinstance(data, dict):
            return {"name": name, "avatar_url": avatar}
        inner = data.get("data")
        if not isinstance(inner, dict):
            inner = data
        name = str(inner.get("name") or "").strip()
        avatar = str(inner.get("avatar") or inner.get("oa_avatar") or "").strip()
    except Exception:
        logger.debug("Zalo OA profile fetch failed", exc_info=True)
    return {"name": name, "avatar_url": avatar}
