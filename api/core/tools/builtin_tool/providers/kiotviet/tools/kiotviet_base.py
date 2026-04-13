"""Base class for KiotViet tools with shared client initialization."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.kiotviet_client import KiotVietAPIError, KiotVietClient
from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotVietBaseTool(BuiltinTool):
    """Shared base for all KiotViet tools."""

    def _get_client(self) -> KiotVietClient:
        if not self.runtime or not self.runtime.credentials:
            raise ValueError("KiotViet credentials are not configured")
        creds = self.runtime.credentials
        return KiotVietClient(
            client_id=creds.get("client_id", ""),
            client_secret=creds.get("client_secret", ""),
            retailer_name=creds.get("retailer_name", ""),
        )

    @staticmethod
    def _parse_json_param(value: str | None) -> Any:
        """Parse a JSON string parameter, return None if empty."""
        if not value or not value.strip():
            return None
        return json.loads(value)

    def _invoke_api(
        self, call: Any, error_prefix: str = "KiotViet API error"
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Wrap an API call, yielding a JSON message on success or text error."""
        try:
            result = call()
            if result is None:
                yield self.create_text_message("Operation completed successfully.")
            elif isinstance(result, dict):
                yield self.create_json_message(result)
            else:
                yield self.create_text_message(json.dumps(result, ensure_ascii=False, default=str))
        except KiotVietAPIError as e:
            yield self.create_text_message(f"{error_prefix}: {e}")
        except Exception as e:
            yield self.create_text_message(f"{error_prefix}: {e}")
