from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietCategoriesTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/categories", params))

            elif action == "get":
                cid = int(tool_parameters["category_id"])
                yield from self._invoke_api(lambda: client.get(f"/categories/{cid}"))

            elif action == "create":
                data: dict[str, Any] = {"categoryName": tool_parameters["category_name"]}
                if tool_parameters.get("parent_id"):
                    data["parentId"] = int(tool_parameters["parent_id"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                yield from self._invoke_api(lambda: client.post("/categories", data))

            elif action == "update":
                cid = int(tool_parameters["category_id"])
                data: dict[str, Any] = {}
                if tool_parameters.get("category_name"):
                    data["categoryName"] = tool_parameters["category_name"]
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                yield from self._invoke_api(lambda: client.put(f"/categories/{cid}", data))

            elif action == "delete":
                cid = int(tool_parameters["category_id"])
                yield from self._invoke_api(lambda: client.delete(f"/categories/{cid}"))

            elif action == "get_hierarchical":
                params = {"hierarchicalData": True}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/categories", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
