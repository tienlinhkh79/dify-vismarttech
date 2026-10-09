"""Facebook Graph API /me/messages send with delivery modes and readable errors."""

from __future__ import annotations

from typing import Any, Literal

import httpx

from core.helper.ssrf_proxy import ssrf_proxy

MessengerSendDelivery = Literal["standard", "human_agent"]

_OUTSIDE_WINDOW_CODES = frozenset({551})
_OUTSIDE_WINDOW_SUBCODES = frozenset({1545041})


def is_outside_messaging_window_error(response: httpx.Response) -> bool:
    try:
        body = response.json()
    except Exception:
        return False
    if not isinstance(body, dict):
        return False
    error = body.get("error")
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    if code in _OUTSIDE_WINDOW_CODES:
        return True
    return error.get("error_subcode") in _OUTSIDE_WINDOW_SUBCODES


def format_graph_send_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except Exception:
        return f"Facebook Messenger rejected the message (HTTP {response.status_code})."
    if not isinstance(body, dict):
        return f"Facebook Messenger rejected the message (HTTP {response.status_code})."
    error = body.get("error")
    if not isinstance(error, dict):
        return f"Facebook Messenger rejected the message (HTTP {response.status_code})."
    message = str(error.get("message") or "").strip()
    code = error.get("code")
    if code in _OUTSIDE_WINDOW_CODES or error.get("error_subcode") in _OUTSIDE_WINDOW_SUBCODES:
        return (
            "Facebook từ chối gửi tin qua Messenger (551). Thường do: (1) hết cửa sổ 24 giờ kể từ "
            "lần khách nhắn Page gần nhất; (2) App Meta đang ở chế độ Development — chỉ gửi được "
            "cho tài khoản có vai trò trên App (Admin/Developer/Tester) hoặc cần chuyển App sang "
            "Live và được duyệt quyền pages_messaging; (3) khách chặn Page hoặc chỉ tương tác "
            "qua bình luận. Thử trả lời trực tiếp trên Meta Business Suite; nếu được thì kiểm tra "
            "Settings → Inboxes (webhook + token Page)."
        )
    if message:
        return f"Facebook Messenger: {message}"
    return f"Facebook Messenger rejected the message (HTTP {response.status_code})."


def post_messenger_message(
    *,
    graph_api_version: str,
    page_access_token: str,
    payload: dict[str, Any],
    delivery: MessengerSendDelivery = "standard",
) -> None:
    endpoint = f"https://graph.facebook.com/{graph_api_version}/me/messages"
    params = {"access_token": page_access_token}
    headers = {"Content-Type": "application/json"}

    attempts: list[dict[str, Any]] = [
        {**payload, "messaging_type": "RESPONSE"},
        {**payload, "messaging_type": "MESSAGE_TAG", "tag": "HUMAN_AGENT"},
    ]

    last_response: httpx.Response | None = None
    for index, attempt_payload in enumerate(attempts):
        response = ssrf_proxy.post(endpoint, params=params, json=attempt_payload, headers=headers)
        if response.is_success:
            return
        last_response = response
        if index == 0 and is_outside_messaging_window_error(response) and len(attempts) > 1:
            continue
        break

    if last_response is None:
        raise ValueError("Facebook Messenger send failed.")
    raise ValueError(format_graph_send_error(last_response))
