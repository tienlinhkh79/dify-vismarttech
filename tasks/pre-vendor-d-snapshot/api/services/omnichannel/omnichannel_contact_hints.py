"""Heuristics to infer customer display names from omnichannel chat text."""

from __future__ import annotations

import re

_NAME_LINE_PATTERN = re.compile(
    r"(?im)^(?:name|ten|họ tên|ho ten|full name|customer name)\s*[:：]\s*(.+?)\s*$"
)
_NAME_INLINE_PATTERN = re.compile(
    r"(?im)(?:name|ten|họ tên|ho ten|full name|customer name)\s*[:：]\s*([^,\n\r]+)"
)
_UUID_LIKE_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def normalize_display_name(value: str | None) -> str | None:
    cleaned = " ".join((value or "").strip().split())
    if not cleaned or len(cleaned) > 120:
        return None
    lowered = cleaned.lower()
    if lowered in {"unknown", "guest", "anonymous", "n/a", "na"}:
        return None
    if _UUID_LIKE_PATTERN.fullmatch(cleaned):
        return None
    if cleaned.isdigit():
        return None
    return cleaned


def extract_display_name_from_text(text: str) -> str | None:
    if not text.strip():
        return None
    for pattern in (_NAME_LINE_PATTERN, _NAME_INLINE_PATTERN):
        match = pattern.search(text)
        if not match:
            continue
        candidate = normalize_display_name(match.group(1))
        if candidate:
            return candidate
    return None


def looks_like_anonymous_display(value: str | None, *, external_user_id: str) -> bool:
    current = (value or "").strip()
    if not current:
        return True
    ext = (external_user_id or "").strip()
    if ext and current == ext:
        return True
    if _UUID_LIKE_PATTERN.fullmatch(current):
        return True
    return False
