from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.providers.kiotviet.tools.kiotviet_base import KiotVietBaseTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class KiotvietWebhooksTool(KiotVietBaseTool):
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
                yield from self._invoke_api(lambda: client.get("/webhooks", params))

            elif action == "get":
                wid = int(tool_parameters["webhook_id"])
                yield from self._invoke_api(lambda: client.get(f"/webhooks/{wid}"))

            elif action == "create":
                data: dict[str, Any] = {
                    "url": tool_parameters["url"],
                    "secret": tool_parameters.get("secret", ""),
                    "isActive": True,
                }
                events = self._parse_json_param(tool_parameters.get("events"))
                if events:
                    data["events"] = events
                yield from self._invoke_api(lambda: client.post("/webhooks", data))

            elif action == "update":
                wid = int(tool_parameters["webhook_id"])
                data: dict[str, Any] = {"id": wid}
                if tool_parameters.get("url"):
                    data["url"] = tool_parameters["url"]
                if tool_parameters.get("secret"):
                    data["secret"] = tool_parameters["secret"]
                events = self._parse_json_param(tool_parameters.get("events"))
                if events:
                    data["events"] = events
                yield from self._invoke_api(lambda: client.put(f"/webhooks/{wid}", data))

            elif action == "delete":
                wid = int(tool_parameters["webhook_id"])
                yield from self._invoke_api(lambda: client.delete(f"/webhooks/{wid}"))

            elif action == "enable":
                wid = int(tool_parameters["webhook_id"])
                yield from self._invoke_api(
                    lambda: client.put(f"/webhooks/{wid}", {"id": wid, "isActive": True})
                )

            elif action == "disable":
                wid = int(tool_parameters["webhook_id"])
                yield from self._invoke_api(
                    lambda: client.put(f"/webhooks/{wid}", {"id": wid, "isActive": False})
                )

            else:
                yield self.create_text_message(f"Unknown action: {action}")
        finally:
            client.close()


del KiotVietBaseTool
