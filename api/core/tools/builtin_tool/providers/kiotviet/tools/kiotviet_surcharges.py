from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietSurchargesTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/surcharges", params))

            elif action == "get":
                sid = int(tool_parameters["surcharge_id"])
                yield from self._invoke_api(lambda: client.get(f"/surcharges/{sid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "name": tool_parameters["name"],
                    "value": float(tool_parameters["value"]),
                    "isPercent": bool(tool_parameters.get("is_percent", False)),
                }
                yield from self._invoke_api(lambda: client.post("/surcharges", data))

            elif action == "update":
                sid = int(tool_parameters["surcharge_id"])
                data: dict[str, Any] = {}
                if tool_parameters.get("name"):
                    data["name"] = tool_parameters["name"]
                if tool_parameters.get("value") is not None:
                    data["value"] = float(tool_parameters["value"])
                if tool_parameters.get("is_percent") is not None:
                    data["isPercent"] = bool(tool_parameters["is_percent"])
                yield from self._invoke_api(lambda: client.put(f"/surcharges/{sid}", data))

            elif action == "delete":
                sid = int(tool_parameters["surcharge_id"])
                yield from self._invoke_api(lambda: client.delete(f"/surcharges/{sid}"))

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
