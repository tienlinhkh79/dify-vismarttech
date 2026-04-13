from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietVouchersTool(KiotVietBaseTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        client = self._get_client()
        action = tool_parameters.get("action", "list_campaigns")

        try:
            if action == "list_campaigns":
                params: dict[str, Any] = {}
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/vouchers/campaigns", params))

            elif action == "get_campaign":
                cid = int(tool_parameters["campaign_id"])
                yield from self._invoke_api(lambda: client.get(f"/vouchers/campaigns/{cid}"))

            elif action == "create_campaign":
                data: dict[str, Any] = {
                    "code": tool_parameters["code"],
                    "name": tool_parameters["name"],
                    "startDate": tool_parameters["start_date"],
                    "endDate": tool_parameters["end_date"],
                    "branchId": int(tool_parameters["branch_id"]),
                }
                if tool_parameters.get("discount_type"):
                    data["discountType"] = int(tool_parameters["discount_type"])
                if tool_parameters.get("discount_value"):
                    data["discountValue"] = float(tool_parameters["discount_value"])
                if tool_parameters.get("quantity"):
                    data["quantity"] = int(tool_parameters["quantity"])
                yield from self._invoke_api(lambda: client.post("/vouchers/campaigns", data))

            elif action == "update_campaign":
                cid = int(tool_parameters["campaign_id"])
                data: dict[str, Any] = {"id": cid}
                if tool_parameters.get("name"):
                    data["name"] = tool_parameters["name"]
                if tool_parameters.get("end_date"):
                    data["endDate"] = tool_parameters["end_date"]
                if tool_parameters.get("discount_value"):
                    data["discountValue"] = float(tool_parameters["discount_value"])
                yield from self._invoke_api(lambda: client.put(f"/vouchers/campaigns/{cid}", data))

            elif action == "delete_campaign":
                cid = int(tool_parameters["campaign_id"])
                yield from self._invoke_api(lambda: client.delete(f"/vouchers/campaigns/{cid}"))

            elif action == "list_vouchers":
                params = {}
                if tool_parameters.get("campaign_id"):
                    params["campaignId"] = int(tool_parameters["campaign_id"])
                if tool_parameters.get("page_size"):
                    params["pageSize"] = int(tool_parameters["page_size"])
                yield from self._invoke_api(lambda: client.get("/vouchers", params))

            elif action == "get_voucher":
                vid = int(tool_parameters["voucher_id"])
                yield from self._invoke_api(lambda: client.get(f"/vouchers/{vid}"))

            elif action == "get_voucher_by_code":
                code = tool_parameters["code"]
                yield from self._invoke_api(lambda: client.get(f"/vouchers/code/{code}"))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
