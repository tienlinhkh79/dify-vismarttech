"""Base class for Sapo tools with shared client initialization."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.sapo.sapo_client import SapoAPIError, SapoClient
from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class SapoBaseTool(BuiltinTool):
    """Shared helper methods for all Sapo tools."""

    def _get_client(self) -> SapoClient:
        if not self.runtime or not self.runtime.credentials:
            raise ValueError("Sapo credentials are not configured")
        creds = self.runtime.credentials
        return SapoClient(
            store=creds.get("store", ""),
            access_token=creds.get("access_token", ""),
        )

    @staticmethod
    def _parse_json_param(value: str | None) -> Any:
        if not value or not value.strip():
            return None
        return json.loads(value)

    def _invoke_api(
        self, call: Any, error_prefix: str = "Sapo API error"
    ) -> Generator[ToolInvokeMessage, None, None]:
        try:
            result = call()
            if result is None:
                yield self.create_text_message("Operation completed successfully.")
            elif isinstance(result, dict):
                yield self.create_json_message(result)
            else:
                yield self.create_text_message(json.dumps(result, ensure_ascii=False, default=str))
        except SapoAPIError as e:
            yield self.create_text_message(f"{error_prefix}: {e}")
        except Exception as e:
            yield self.create_text_message(f"{error_prefix}: {e}")
