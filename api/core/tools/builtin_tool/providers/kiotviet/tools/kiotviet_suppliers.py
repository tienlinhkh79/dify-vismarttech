from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietSuppliersTool(KiotVietBaseTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        client = self._get_client()
        action = tool_parameters.get("action", "list")

        try:
            if action == "list":
                params: dict[str, Any] = {}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                if tool_parameters.get("name"):
                    params["name"] = tool_parameters["name"]
                if tool_parameters.get("code"):
                    params["code"] = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get("/suppliers", params))

            elif action == "get":
                sid = int(tool_parameters["supplier_id"])
                yield from self._invoke_api(lambda: client.get(f"/suppliers/{sid}"))

            elif action == "get_by_code":
                code = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get(f"/suppliers/code/{code}"))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
