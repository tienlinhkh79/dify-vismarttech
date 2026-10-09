"""Fetch Messenger / Page display fields from Meta Graph (PSID profile, page name/picture)."""

from __future__ import annotations

import logging
from typing import Any

from core.helper.ssrf_proxy import ssrf_proxy

logger = logging.getLogger(__name__)


def extract_graph_picture_url(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    data = node.get("data")
    if isinstance(data, dict):
        u = data.get("url")
        return str(u).strip() if u else ""
    u = node.get("url")
    return str(u).strip() if u else ""


def _fetch_psid_picture_edge(*, psid: str, access_token: str, graph_version: str) -> str:
    """Fallback: Graph `/{psid}/picture?redirect=false` (ProfilePictureSource) when `profile_pic` field is absent."""
    ver = (graph_version or "v23.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{ver}/{psid}/picture"
    try:
        response = ssrf_proxy.get(
            url,
            params={"redirect": "false", "type": "large", "access_token": access_token},
            timeout=(5, 15),
        )
        if response.status_code >= 400:
            return ""
        payload = response.json()
        if not isinstance(payload, dict):
            return ""
        if payload.get("error"):
            return ""
        pic = extract_graph_picture_url(payload)
        if pic and isinstance(payload.get("data"), dict) and payload["data"].get("is_silhouette") is True:
            return ""
        return pic
    except Exception:
        logger.debug("Messenger Graph PSID /picture edge failed psid=%s", psid, exc_info=True)
    return ""


def fetch_messenger_user_profile(*, psid: str, access_token: str, graph_version: str) -> dict[str, str]:
    """Resolve PSID to display name and profile picture URL (Page-scoped token)."""
    name = ""
    profile_pic = ""
    psid = (psid or "").strip()
    if not psid or not access_token:
        return {"name": name, "profile_pic": profile_pic}
    ver = (graph_version or "v23.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{ver}/{psid}"
    try:
        response = ssrf_proxy.get(
            url,
            params={
                "fields": "name,first_name,last_name,profile_pic,picture",
                "access_token": access_token,
            },
            timeout=(5, 15),
        )
        if response.status_code >= 400:
            logger.warning(
                "Messenger Graph user profile HTTP %s psid=%s body_prefix=%r",
                response.status_code,
                psid,
                (response.text or "")[:400],
            )
            return {"name": name, "profile_pic": profile_pic}
        data = response.json()
        if not isinstance(data, dict):
            logger.warning(
                "Messenger Graph user profile unexpected JSON type psid=%s type=%s",
                psid,
                type(data).__name__,
            )
            return {"name": name, "profile_pic": profile_pic}
        if err := data.get("error"):
            logger.warning("Messenger Graph user profile error object psid=%s error=%r", psid, err)
            return {"name": name, "profile_pic": profile_pic}
        name = str(data.get("name") or "").strip()
        if not name:
            fn = str(data.get("first_name") or "").strip()
            ln = str(data.get("last_name") or "").strip()
            name = (fn + " " + ln).strip()
        profile_pic = str(data.get("profile_pic") or "").strip()
        if not profile_pic:
            profile_pic = extract_graph_picture_url(data.get("picture"))
        if not profile_pic:
            profile_pic = _fetch_psid_picture_edge(psid=psid, access_token=access_token, graph_version=graph_version)
        if not profile_pic and not name:
            logger.warning(
                "Messenger Graph user profile returned empty profile (no name, no picture) psid=%s "
                "response_keys=%s — check Business Asset User Profile Access, App Review, and Page "
                "Settings → Advanced Messaging → Info About People for this Page",
                psid,
                sorted(data.keys()),
            )
        elif not profile_pic:
            logger.info("Messenger Graph user profile has display name but no profile_pic psid=%s", psid)
    except Exception:
        logger.warning("Messenger Graph user profile request failed psid=%s", psid, exc_info=True)
    return {"name": name, "profile_pic": profile_pic}


def fetch_page_profile(*, page_id: str, access_token: str, graph_version: str) -> dict[str, str]:
    """Resolve Page ID to name and picture URL."""
    display_name = ""
    picture_url = ""
    page_id = (page_id or "").strip()
    if not page_id or not access_token:
        return {"name": display_name, "picture_url": picture_url}
    ver = (graph_version or "v23.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{ver}/{page_id}"
    try:
        response = ssrf_proxy.get(
            url,
            params={"fields": "name,picture", "access_token": access_token},
            timeout=(5, 15),
        )
        response.raise_for_status()
        data = response.json()
        display_name = str(data.get("name") or "").strip()
        picture_url = extract_graph_picture_url(data.get("picture"))
    except Exception:
        logger.debug("Messenger Graph page profile failed page_id=%s", page_id, exc_info=True)
    return {"name": display_name, "picture_url": picture_url}
