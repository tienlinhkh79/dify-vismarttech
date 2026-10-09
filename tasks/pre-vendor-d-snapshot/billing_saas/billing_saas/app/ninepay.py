"""9Pay hosted payment portal URL builder (matches official sample-javascript on GitLab).

Signature string: POST\\n{endpoint}/payments/create\\n{time}\\n{sorted_urlencoded_params}
Portal URL: {endpoint}/portal?baseEncode={b64_json}&signature={hmac_b64}
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Mapping
from urllib.parse import quote_plus, urlencode


def _sorted_form_body(params: Mapping[str, str | int | float]) -> str:
    """Alphabetical key order, same as sample ``buildHttpQuery``."""
    ordered = dict(sorted(params.items(), key=lambda kv: kv[0]))
    pairs: list[tuple[str, str]] = []
    for k, v in ordered.items():
        pairs.append((str(k), str(v)))
    return urlencode(pairs, quote_via=quote_plus)


def build_signature_message(endpoint_base: str, unix_time: int, params: Mapping[str, str | int | float]) -> str:
    base = endpoint_base.rstrip("/")
    path = f"{base}/payments/create"
    query = _sorted_form_body(params)
    return f"POST\n{path}\n{unix_time}\n{query}"


def sign_request(secret_key: str, message: str) -> str:
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def build_portal_redirect_url(
    *,
    endpoint_base: str,
    merchant_key: str,
    secret_key: str,
    unix_time: int,
    invoice_no: str,
    amount_vnd: int,
    description: str,
    return_url: str,
    back_url: str | None = None,
    method: str | None = None,
    transaction_type: str | None = None,
    lang: str | None = None,
    currency: str | None = None,
    bank_code: str | None = None,
    profile_id: int | None = None,
    card_origin_allow: int | None = None,
    card_brand_allow: str | None = None,
    bin_allow: str | None = None,
    card_type_allow: str | None = None,
    campaign_id: str | None = None,
) -> str:
    """Return full URL to open in the browser (customer is redirected to 9Pay)."""
    params: dict[str, str | int] = {
        "merchantKey": merchant_key,
        "time": unix_time,
        "invoice_no": invoice_no,
        "amount": int(amount_vnd),
        "description": description,
        "return_url": return_url,
        "back_url": back_url or return_url,
    }
    if method:
        params["method"] = method
    if transaction_type:
        params["transaction_type"] = transaction_type
    if lang:
        params["lang"] = lang
    if currency:
        params["currency"] = currency
    if bank_code:
        params["bank_code"] = bank_code
    if profile_id is not None:
        params["profile_id"] = int(profile_id)
    if card_origin_allow is not None:
        params["card_origin_allow"] = int(card_origin_allow)
    if card_brand_allow:
        params["card_brand_allow"] = card_brand_allow
    if bin_allow:
        params["bin_allow"] = bin_allow
    if card_type_allow:
        params["card_type_allow"] = card_type_allow
    if campaign_id:
        params["campaign_id"] = campaign_id

    message = build_signature_message(endpoint_base, unix_time, params)
    signature = sign_request(secret_key, message)
    payload_json = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
    base_encode = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
    portal_query = _sorted_form_body({"baseEncode": base_encode, "signature": signature})
    return f"{endpoint_base.rstrip('/')}/portal?{portal_query}"


def verify_ipn_checksum(result_b64: str, checksum_hex_upper: str, checksum_key: str) -> bool:
    """IPN checksum: UPPERCASE(SHA256_hex(result + checksum_key)) per 9Pay PHP samples."""
    expected = hashlib.sha256((result_b64 + checksum_key).encode("utf-8")).hexdigest().upper()
    return hmac.compare_digest(expected, checksum_hex_upper.upper())


def decode_ipn_result(result_b64: str) -> dict[str, Any]:
    raw = base64.b64decode(result_b64)
    return json.loads(raw.decode("utf-8"))


def is_payment_success_status(status: int) -> bool:
    """Transaction success for collection flow (see 9Pay status table)."""
    return status == 5
