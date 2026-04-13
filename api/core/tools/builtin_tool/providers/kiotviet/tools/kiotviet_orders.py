import re
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietOrdersTool(KiotVietBaseTool):
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
                status = self._parse_json_param(tool_parameters.get("status"))
                if status:
                    params["status"] = status
                yield from self._invoke_api(lambda: client.get("/orders", params))

            elif action == "get":
                oid = int(tool_parameters["order_id"])
                yield from self._invoke_api(lambda: client.get(f"/orders/{oid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "branchId": int(tool_parameters["branch_id"]),
                }
                if tool_parameters.get("customer_id"):
                    data["customerId"] = int(tool_parameters["customer_id"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                if tool_parameters.get("discount"):
                    data["discount"] = float(tool_parameters["discount"])
                order_details = self._parse_json_param(tool_parameters.get("order_details"))
                if order_details:
                    data["orderDetails"] = order_details
                yield from self._invoke_api(lambda: client.post("/orders", data))

            elif action == "update":
                oid = int(tool_parameters["order_id"])
                data = {"id": oid}
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                if tool_parameters.get("discount"):
                    data["discount"] = float(tool_parameters["discount"])
                order_details = self._parse_json_param(tool_parameters.get("order_details"))
                if order_details:
                    data["orderDetails"] = order_details
                yield from self._invoke_api(lambda: client.put(f"/orders/{oid}", data))

            elif action == "cancel":
                oid = int(tool_parameters["order_id"])
                data = {
                    "id": oid,
                    "status": 4,  # Cancelled
                    "description": tool_parameters.get("description", ""),
                }
                yield from self._invoke_api(lambda: client.put(f"/orders/{oid}", data))

            elif action == "delete":
                oid = int(tool_parameters["order_id"])
                yield from self._invoke_api(lambda: client.delete(f"/orders/{oid}"))

            elif action == "get_by_code":
                code = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get(f"/orders/code/{code}"))

            elif action == "get_by_date_range":
                params = {
                    "fromPurchaseDate": tool_parameters["from_date"],
                    "toPurchaseDate": tool_parameters["to_date"],
                }
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/orders", params))

            elif action == "get_by_customer":
                identifier = tool_parameters["customer_identifier"]
                is_phone = bool(re.match(r"^\d+$", identifier))
                params = {}
                if is_phone:
                    params["customerPhone"] = identifier
                else:
                    params["customerCode"] = identifier
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/orders", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
