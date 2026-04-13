import re
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietInvoicesTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/invoices", params))

            elif action == "get":
                iid = int(tool_parameters["invoice_id"])
                yield from self._invoke_api(lambda: client.get(f"/invoices/{iid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "branchId": int(tool_parameters["branch_id"]),
                }
                if tool_parameters.get("customer_id"):
                    data["customerId"] = int(tool_parameters["customer_id"])
                if tool_parameters.get("total_payment"):
                    data["totalPayment"] = float(tool_parameters["total_payment"])
                if tool_parameters.get("description"):
                    data["description"] = tool_parameters["description"]
                invoice_details = self._parse_json_param(tool_parameters.get("invoice_details"))
                if invoice_details:
                    data["invoiceDetails"] = invoice_details
                yield from self._invoke_api(lambda: client.post("/invoices", data))

            elif action == "cancel":
                iid = int(tool_parameters["invoice_id"])
                data = {
                    "id": iid,
                    "status": 4,  # Cancelled
                    "description": tool_parameters.get("description", ""),
                }
                yield from self._invoke_api(lambda: client.put(f"/invoices/{iid}", data))

            elif action == "delete":
                iid = int(tool_parameters["invoice_id"])
                yield from self._invoke_api(
                    lambda: client.delete("/invoices", {"id": iid, "isVoidPayment": True})
                )

            elif action == "get_by_code":
                code = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get(f"/invoices/code/{code}"))

            elif action == "get_by_date_range":
                params = {
                    "fromPurchaseDate": tool_parameters["from_date"],
                    "toPurchaseDate": tool_parameters["to_date"],
                }
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/invoices", params))

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
                yield from self._invoke_api(lambda: client.get("/invoices", params))

            elif action == "get_by_order":
                params = {"orderId": int(tool_parameters["order_id"])}
                yield from self._invoke_api(lambda: client.get("/invoices", params))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
