"""Helpers for chat user query vs human-readable display text (rich-reply buttons)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_display_query_from_args(args: Mapping[str, Any]) -> str | None:
    """Return display text when it differs from the workflow routing query."""
    raw = args.get("display_query")
    if not isinstance(raw, str):
        return None
    display = raw.strip()
    query = str(args.get("query") or "").strip()
    if not display or display == query:
        return None
    return display


def merge_display_query_into_metadata(metadata: dict[str, Any], display_query: str | None) -> dict[str, Any]:
    if not display_query:
        return metadata
    merged = dict(metadata)
    merged["display_query"] = display_query
    return merged
