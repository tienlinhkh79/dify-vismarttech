from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietBranchesTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/branches", params))

            elif action == "get":
                bid = int(tool_parameters["branch_id"])
                yield from self._invoke_api(lambda: client.get(f"/branches/{bid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "name": tool_parameters["name"],
                    "address": tool_parameters.get("address", ""),
                }
                if tool_parameters.get("phone_number"):
                    data["phoneNumber"] = tool_parameters["phone_number"]
                if tool_parameters.get("email"):
                    data["email"] = tool_parameters["email"]
                yield from self._invoke_api(lambda: client.post("/branches", data))

            elif action == "update":
                bid = int(tool_parameters["branch_id"])
                data: dict[str, Any] = {}
                if tool_parameters.get("name"):
                    data["name"] = tool_parameters["name"]
                if tool_parameters.get("address"):
                    data["address"] = tool_parameters["address"]
                if tool_parameters.get("phone_number"):
                    data["phoneNumber"] = tool_parameters["phone_number"]
                yield from self._invoke_api(lambda: client.put(f"/branches/{bid}", data))

            elif action == "delete":
                bid = int(tool_parameters["branch_id"])
                yield from self._invoke_api(lambda: client.delete(f"/branches/{bid}"))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
