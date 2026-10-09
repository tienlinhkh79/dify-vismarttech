"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mcp_url: str
    proxy_api_key: str
    request_timeout_seconds: float
    answer_timeout_ms: int
    image_dir: str
    public_image_url: str


def load_settings() -> Settings:
    mcp_url = os.environ.get("NOTEBOOKLM_MCP_URL", "http://notebooklm-mcp:8010/mcp").rstrip("/")
    proxy_api_key = os.environ.get("NOTEBOOKLM_PROXY_API_KEY", "").strip()
    if not proxy_api_key:
        raise RuntimeError("NOTEBOOKLM_PROXY_API_KEY is required")

    timeout_raw = os.environ.get("NOTEBOOKLM_PROXY_TIMEOUT_SECONDS", "120")
    answer_timeout_raw = os.environ.get("NOTEBOOKLM_ANSWER_TIMEOUT_MS", "600000")
    image_dir = os.environ.get("NOTEBOOKLM_IMAGE_DIR", "/app/data/images")
    public_image_url = os.environ.get(
        "NOTEBOOKLM_PUBLIC_IMAGE_URL",
        "https://chatbotai.vismarttech.com/notebooklm-images",
    ).rstrip("/")

    return Settings(
        mcp_url=mcp_url,
        proxy_api_key=proxy_api_key,
        request_timeout_seconds=float(timeout_raw),
        answer_timeout_ms=int(answer_timeout_raw),
        image_dir=image_dir,
        public_image_url=public_image_url,
    )
