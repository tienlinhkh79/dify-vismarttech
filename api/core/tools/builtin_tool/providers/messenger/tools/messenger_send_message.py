from __future__ import annotations

from collections.abc import Generator
from typing import Any

import httpx

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class MessengerSendMessageTool(BuiltinTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        recipient_id = str(tool_parameters.get("recipient_id", "")).strip()
        message_text = str(tool_parameters.get("message_text", "")).strip()

        if not recipient_id:
            yield self.create_text_message("recipient_id is required")
            return
        if not message_text:
            yield self.create_text_message("message_text is required")
            return

        credentials = self.runtime.credentials or {}
        page_access_token = str(credentials.get("page_access_token", "")).strip()
        graph_api_version = str(credentials.get("graph_api_version", "v23.0")).strip() or "v23.0"

        if not page_access_token:
            yield self.create_text_message("Missing provider credential: page_access_token")
            return

        endpoint = f"https://graph.facebook.com/{graph_api_version}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": message_text},
        }
        try:
            response = httpx.post(
                endpoint,
                params={"access_token": page_access_token},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            msg_id = body.get("message_id")
            yield self.create_text_message(f"Message sent successfully. message_id={msg_id}")
        except Exception as e:
            yield self.create_text_message(f"Failed to send message: {e}")
