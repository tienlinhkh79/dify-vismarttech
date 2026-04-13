from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietCustomersTool(KiotVietBaseTool):
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
                if tool_parameters.get("current_item") is not None:
                    params["currentItem"] = int(tool_parameters["current_item"])
                yield from self._invoke_api(lambda: client.get("/customers", params))

            elif action == "get":
                cid = int(tool_parameters["customer_id"])
                yield from self._invoke_api(lambda: client.get(f"/customers/{cid}"))

            elif action == "create":
                data: dict[str, Any] = {"name": tool_parameters["name"]}
                if tool_parameters.get("contact_number"):
                    data["contactNumber"] = tool_parameters["contact_number"]
                if tool_parameters.get("email"):
                    data["email"] = tool_parameters["email"]
                if tool_parameters.get("address"):
                    data["address"] = tool_parameters["address"]
                yield from self._invoke_api(lambda: client.post("/customers", data))

            elif action == "search":
                params = {"keyword": tool_parameters.get("keyword", "")}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/customers", params))

            elif action == "get_by_phone":
                params = {
                    "contactNumber": tool_parameters["contact_number"],
                    "pageSize": 1,
                }
                yield from self._invoke_api(lambda: client.get("/customers", params))

            elif action == "get_by_group":
                params = {"customerGroupId": int(tool_parameters["group_id"])}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/customers", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
