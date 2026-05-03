"""9Pay REST API signing (PHP MessageBuilder + HMACSignature sample parity).

References:
- https://gitlab.com/9pay-sample/sample-php/-/blob/main/lib/MessageBuilder.php
- https://gitlab.com/9pay-sample/sample-php/-/blob/main/lib/HMACSignature.php
- https://developers.9pay.vn/danh-sach-api/kiem-tra-trang-thai-giao-dich
- https://developers.9pay.vn/danh-sach-api/hoan-tien-giao-dich-69
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Mapping
from urllib.parse import quote

logger = logging.getLogger(__name__)


def _canonical_params(params: Mapping[str, Any]) -> str:
    if not params:
        return ""
    parts: list[str] = []
    for key in sorted(params.keys(), key=lambda k: str(k)):
        k = str(key)
        v = str(params[key])
        parts.append(f"{quote(k, safe='')}={quote(v, safe='')}")
    return "&".join(parts)


def build_rest_message(
    method: str,
    uri: str,
    date_value: int | str,
    *,
    params: Mapping[str, Any] | None = None,
    body: str | None = None,
) -> str:
    """Build the UTF-8 string that is HMAC-SHA256 signed for Authorization (same as PHP MessageBuilder.build)."""
    method_u = method.upper().strip()
    date_s = str(date_value)
    headers_canonical = ""
    if method_u == "POST" and body:
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        canonical_payload = base64.b64encode(digest).decode("ascii")
    else:
        canonical_payload = _canonical_params(params or {})
    parts = [method_u, uri, date_s]
    if headers_canonical:
        parts.append(headers_canonical)
    if canonical_payload:
        parts.append(canonical_payload)
    return "\n".join(parts)


def sign_rest_authorization(*, message: str, merchant_secret: str) -> str:
    """Return base64(HMAC-SHA256(message, secret)) — matches PHP HMACSignature.sign."""
    raw = hmac.new(merchant_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(raw).decode("ascii")


def authorization_header(*, merchant_key: str, signature_b64: str) -> str:
    return (
        "Signature "
        f"Algorithm=HS256,Credential={merchant_key},SignedHeaders=,Signature={signature_b64}"
    )


def inquire_payment(
    *,
    endpoint_base: str,
    merchant_key: str,
    merchant_secret: str,
    invoice_no: str,
    unix_time: int,
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    base = endpoint_base.rstrip("/")
    uri = f"{base}/v2/payments/{quote(str(invoice_no), safe='')}/inquire"
    message = build_rest_message("GET", uri, unix_time, params={})
    sig = sign_rest_authorization(message=message, merchant_secret=merchant_secret)
    headers = {
        "Date": str(unix_time),
        "Authorization": authorization_header(merchant_key=merchant_key, signature_b64=sig),
        "Accept": "application/json",
    }
    req = urllib.request.Request(uri, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning("ninepay_inquire_http_error status=%s body=%s", e.code, err_body[:500])
        raise
    return json.loads(raw)


def post_form_v2(
    *,
    endpoint_base: str,
    path: str,
    merchant_key: str,
    merchant_secret: str,
    form_fields: Mapping[str, Any],
    unix_time: int,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """POST application/x-www-form-urlencoded; body must match signed canonical params (PHP sample)."""
    base = endpoint_base.rstrip("/")
    uri = f"{base}{path}"
    fields = dict(form_fields)
    body = _canonical_params(fields)
    message = build_rest_message("POST", uri, unix_time, params=fields)
    sig = sign_rest_authorization(message=message, merchant_secret=merchant_secret)
    headers = {
        "Date": str(unix_time),
        "Authorization": authorization_header(merchant_key=merchant_key, signature_b64=sig),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json",
    }
    req = urllib.request.Request(
        uri,
        data=body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def create_refund(
    *,
    endpoint_base: str,
    merchant_key: str,
    merchant_secret: str,
    request_id: str,
    payment_no: int | str,
    amount: int | str,
    description: str,
    unix_time: int,
    bank: str | None = None,
    account_number: str | None = None,
    customer_name: str | None = None,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """POST /v2/refunds/create (see 9Pay doc; bank_* required for transfer refunds)."""
    fields: dict[str, Any] = {
        "request_id": request_id,
        "payment_no": payment_no,
        "amount": amount,
        "description": description,
    }
    if bank:
        fields["bank"] = bank
    if account_number:
        fields["account_number"] = account_number
    if customer_name:
        fields["customer_name"] = customer_name
    return post_form_v2(
        endpoint_base=endpoint_base,
        path="/v2/refunds/create",
        merchant_key=merchant_key,
        merchant_secret=merchant_secret,
        form_fields=fields,
        unix_time=unix_time,
        timeout_sec=timeout_sec,
    )


def inquire_refund(
    *,
    endpoint_base: str,
    merchant_key: str,
    merchant_secret: str,
    request_id: str,
    unix_time: int,
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    """GET /v2/refunds/{request_id}/inquire."""
    base = endpoint_base.rstrip("/")
    rid = quote(str(request_id), safe="")
    uri = f"{base}/v2/refunds/{rid}/inquire"
    message = build_rest_message("GET", uri, unix_time, params={})
    sig = sign_rest_authorization(message=message, merchant_secret=merchant_secret)
    headers = {
        "Date": str(unix_time),
        "Authorization": authorization_header(merchant_key=merchant_key, signature_b64=sig),
        "Accept": "application/json",
    }
    req = urllib.request.Request(uri, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)
