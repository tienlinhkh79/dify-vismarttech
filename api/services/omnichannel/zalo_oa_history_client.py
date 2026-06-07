"""Zalo OA conversation history API (ported from zca-bridge historyClient.ts)."""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict
from urllib.parse import quote

from core.helper.ssrf_proxy import ssrf_proxy

logger = logging.getLogger(__name__)

_LIST_URL = "https://openapi.zalo.me/v2.0/oa/listrecentchat"
_CONV_URL = "https://openapi.zalo.me/v2.0/oa/conversation"


class ZaloRecentChat(TypedDict):
    user_id: str
    last_time_ms: int


def _encode_data(obj: dict[str, Any]) -> str:
    return quote(json.dumps(obj, separators=(",", ":")))


def _get_json(url: str, access_token: str) -> dict[str, Any]:
    response = ssrf_proxy.get(url, params={"access_token": access_token}, timeout=(10, 30))
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Invalid Zalo history response")
    code = int(body.get("error", -1))
    if code != 0:
        raise ValueError(f"Zalo history failed: {code} {body.get('message', '')}".strip())
    return body


def list_recent_chat(*, access_token: str, oa_id: str, offset: int = 0, count: int = 20) -> list[ZaloRecentChat]:
    url = f"{_LIST_URL}?data={_encode_data({'offset': offset, 'count': count})}"
    body = _get_json(url, access_token)
    rows = body.get("data")
    if not isinstance(rows, list):
        return []
    out: list[ZaloRecentChat] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        from_id = str(row.get("from_id") or "")
        to_id = str(row.get("to_id") or "")
        user_id = from_id if from_id and from_id != oa_id else to_id
        if not user_id:
            continue
        out.append({"user_id": user_id, "last_time_ms": int(row.get("time") or 0)})
    return out


def get_conversation_messages(
    *,
    access_token: str,
    user_id: str,
    offset: int = 0,
    count: int = 50,
) -> list[dict[str, Any]]:
    url = f"{_CONV_URL}?data={_encode_data({'user_id': user_id, 'offset': offset, 'count': count})}"
    body = _get_json(url, access_token)
    rows = body.get("data")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
