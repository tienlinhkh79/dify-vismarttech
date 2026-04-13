from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietProductsTool(KiotVietBaseTool):
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
                if tool_parameters.get("category_id"):
                    params["categoryId"] = int(tool_parameters["category_id"])
                if tool_parameters.get("name"):
                    params["name"] = tool_parameters["name"]
                if tool_parameters.get("code"):
                    params["code"] = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get("/products", params))

            elif action == "get":
                pid = int(tool_parameters["product_id"])
                yield from self._invoke_api(lambda: client.get(f"/products/{pid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "name": tool_parameters["name"],
                }
                if tool_parameters.get("code"):
                    data["code"] = tool_parameters["code"]
                if tool_parameters.get("category_id"):
                    data["categoryId"] = int(tool_parameters["category_id"])
                if tool_parameters.get("base_price"):
                    data["basePrice"] = float(tool_parameters["base_price"])
                if tool_parameters.get("retail_price"):
                    data["retailPrice"] = float(tool_parameters["retail_price"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                yield from self._invoke_api(lambda: client.post("/products", data))

            elif action == "update":
                pid = int(tool_parameters["product_id"])
                data = {}
                if tool_parameters.get("name"):
                    data["name"] = tool_parameters["name"]
                if tool_parameters.get("retail_price"):
                    data["retailPrice"] = float(tool_parameters["retail_price"])
                if tool_parameters.get("base_price"):
                    data["basePrice"] = float(tool_parameters["base_price"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                if tool_parameters.get("category_id"):
                    data["categoryId"] = int(tool_parameters["category_id"])
                yield from self._invoke_api(lambda: client.put(f"/products/{pid}", data))

            elif action == "delete":
                pid = int(tool_parameters["product_id"])
                yield from self._invoke_api(lambda: client.delete(f"/products/{pid}"))

            elif action == "search":
                params = {"name": tool_parameters.get("name", "")}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/products", params))

            elif action == "get_by_code":
                code = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get(f"/products/code/{code}"))

            elif action == "get_by_barcode":
                barcode = tool_parameters["barcode"]
                yield from self._invoke_api(
                    lambda: client.get("/products", {"barcode": barcode, "pageSize": 1})
                )

            elif action == "get_inventory":
                params = {}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                branch_ids = self._parse_json_param(tool_parameters.get("branch_ids"))
                if branch_ids:
                    params["branchIds"] = branch_ids
                yield from self._invoke_api(lambda: client.get("/productOnHands", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
