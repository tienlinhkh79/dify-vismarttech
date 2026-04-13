from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietUsersTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/users", params))

            elif action == "get":
                uid = int(tool_parameters["user_id"])
                yield from self._invoke_api(lambda: client.get(f"/users/{uid}"))

            elif action == "search":
                params = {"name": tool_parameters.get("keyword", "")}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/users", params))

            elif action == "get_active":
                params = {"isActive": True}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/users", params))

            elif action == "get_by_branch":
                params = {"branchId": int(tool_parameters["branch_id"])}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/users", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
