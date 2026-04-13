from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietCashflowTool(KiotVietBaseTool):
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
                branch_ids = self._parse_json_param(tool_parameters.get("branch_ids"))
                if branch_ids:
                    params["branchIds"] = branch_ids
                if tool_parameters.get("from_date"):
                    params["startDate"] = tool_parameters["from_date"]
                if tool_parameters.get("to_date"):
                    params["endDate"] = tool_parameters["to_date"]
                yield from self._invoke_api(lambda: client.get("/cashflow", params))

            elif action == "process_payment":
                data: dict[str, Any] = {
                    "invoiceId": int(tool_parameters["invoice_id"]),
                    "amount": float(tool_parameters["amount"]),
                    "method": tool_parameters.get("method", "Cash"),
                }
                yield from self._invoke_api(lambda: client.post("/payments", data))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
