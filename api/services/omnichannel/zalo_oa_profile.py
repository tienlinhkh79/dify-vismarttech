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


def fetch_zalo_user_display(*, access_token: str, user_id: str) -> dict[str, str]:
    """Resolve a Zalo OA end-user display name and avatar (best-effort)."""
    token = (access_token or "").strip()
    uid = (user_id or "").strip()
    if not token or not uid:
        return {"name": "", "avatar_url": ""}
    url = "https://openapi.zalo.me/v3.0/oa/user/detail"
    try:
        response = ssrf_proxy.get(
            url,
            params={"access_token": token, "data": f'{{"user_id":"{uid}"}}'},
            timeout=(5, 15),
        )
        if response.status_code >= 400:
            return {"name": "", "avatar_url": ""}
        data = response.json()
        if not isinstance(data, dict):
            return {"name": "", "avatar_url": ""}
        inner = data.get("data")
        if not isinstance(inner, dict):
            inner = data
        name = str(inner.get("display_name") or inner.get("user_id") or "").strip()
        avatar = str(inner.get("avatar") or "").strip()
    except Exception:
        logger.debug("Zalo user profile fetch failed user_id=%s", uid, exc_info=True)
        return {"name": "", "avatar_url": ""}
    return {"name": name, "avatar_url": avatar}
