from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.sapo.tools.sapo_base import SapoBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class SapoProductsTool(SapoBaseTool):
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
                if tool_parameters.get("limit"):
                    params["limit"] = int(tool_parameters["limit"])
                if tool_parameters.get("page"):
                    params["page"] = int(tool_parameters["page"])
                if tool_parameters.get("query"):
                    params["query"] = tool_parameters["query"]
                if tool_parameters.get("fields"):
                    params["fields"] = tool_parameters["fields"]
                yield from self._invoke_api(lambda: client.get("/admin/products.json", params))

            elif action == "get":
                product_id = int(tool_parameters["product_id"])
                params = {"fields": tool_parameters.get("fields")} if tool_parameters.get("fields") else None
                yield from self._invoke_api(lambda: client.get(f"/admin/products/{product_id}.json", params))

            elif action == "count":
                yield from self._invoke_api(lambda: client.get("/admin/products/count.json"))

            elif action == "create":
                payload = self._parse_json_param(tool_parameters.get("product_payload"))
                if not isinstance(payload, dict):
                    yield self.create_text_message("product_payload must be a JSON object")
                    return
                yield from self._invoke_api(lambda: client.post("/admin/products.json", payload))

            elif action == "update":
                product_id = int(tool_parameters["product_id"])
                payload = self._parse_json_param(tool_parameters.get("product_payload"))
                if not isinstance(payload, dict):
                    yield self.create_text_message("product_payload must be a JSON object")
                    return
                yield from self._invoke_api(lambda: client.put(f"/admin/products/{product_id}.json", payload))

            elif action == "delete":
                product_id = int(tool_parameters["product_id"])
                yield from self._invoke_api(lambda: client.delete(f"/admin/products/{product_id}.json"))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del SapoBaseTool
