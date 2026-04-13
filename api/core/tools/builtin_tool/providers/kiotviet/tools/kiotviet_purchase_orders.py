from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietPurchaseOrdersTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/purchaseorders", params))

            elif action == "get":
                pid = int(tool_parameters["purchase_order_id"])
                yield from self._invoke_api(lambda: client.get(f"/purchaseorders/{pid}"))

            elif action == "create":
                data: dict[str, Any] = {"branchId": int(tool_parameters["branch_id"])}
                if tool_parameters.get("supplier_id"):
                    data["supplierId"] = int(tool_parameters["supplier_id"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                details = self._parse_json_param(tool_parameters.get("purchase_order_details"))
                if details:
                    data["purchaseOrderDetails"] = details
                yield from self._invoke_api(lambda: client.post("/purchaseorders", data))

            elif action == "update":
                pid = int(tool_parameters["purchase_order_id"])
                data: dict[str, Any] = {"id": pid}
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                details = self._parse_json_param(tool_parameters.get("purchase_order_details"))
                if details:
                    data["purchaseOrderDetails"] = details
                yield from self._invoke_api(lambda: client.put(f"/purchaseorders/{pid}", data))

            elif action == "cancel":
                pid = int(tool_parameters["purchase_order_id"])
                data = {
                    "id": pid,
                    "status": 4,  # Cancelled
                    "description": tool_parameters.get("description", ""),
                }
                yield from self._invoke_api(lambda: client.put(f"/purchaseorders/{pid}", data))

            elif action == "get_by_date_range":
                params = {
                    "fromPurchaseDate": tool_parameters["from_date"],
                    "toPurchaseDate": tool_parameters["to_date"],
                }
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/purchaseorders", params))

            elif action == "get_by_supplier":
                params = {"supplierCode": tool_parameters["supplier_code"]}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/purchaseorders", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
