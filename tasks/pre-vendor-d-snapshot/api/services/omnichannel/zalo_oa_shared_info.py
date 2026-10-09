"""Parse Zalo OA user_submit_info payloads (ported from zca-bridge sharedInfo.ts)."""

from __future__ import annotations

from typing import Any, TypedDict


class ZaloContactInfo(TypedDict, total=False):
    name: str
    phone: str
    address: str
    city: str
    district: str


def _str_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _pick_contact(obj: object) -> ZaloContactInfo | None:
    if not isinstance(obj, dict):
        return None
    out: ZaloContactInfo = {}
    name = _str_value(obj.get("name")) or _str_value(obj.get("display_name"))
    phone = _str_value(obj.get("phone")) or _str_value(obj.get("phone_number"))
    address = _str_value(obj.get("address"))
    city = _str_value(obj.get("city"))
    district = _str_value(obj.get("district"))
    if name:
        out["name"] = name
    if phone:
        out["phone"] = phone
    if address:
        out["address"] = address
    if city:
        out["city"] = city
    if district:
        out["district"] = district
    return out or None


def parse_shared_info(src: dict[str, Any]) -> ZaloContactInfo | None:
    message = src.get("message") if isinstance(src.get("message"), dict) else {}
    data = src.get("data") if isinstance(src.get("data"), dict) else {}
    candidates: list[object] = [
        src.get("info"),
        message.get("info") if isinstance(message, dict) else None,
        src.get("shared_info"),
        data.get("shared_info"),
        data.get("info"),
        src,
    ]
    for candidate in candidates:
        picked = _pick_contact(candidate)
        if picked:
            return picked
    return None


def format_shared_info_note(info: ZaloContactInfo) -> str:
    lines = ["📇 Khách chia sẻ thông tin:"]
    if info.get("name"):
        lines.append(f"Tên: {info['name']}")
    if info.get("phone"):
        lines.append(f"SĐT: {info['phone']}")
    if info.get("address"):
        lines.append(f"Địa chỉ: {info['address']}")
    if info.get("city"):
        lines.append(f"Thành phố: {info['city']}")
    if info.get("district"):
        lines.append(f"Quận/Huyện: {info['district']}")
    return "\n".join(lines)
