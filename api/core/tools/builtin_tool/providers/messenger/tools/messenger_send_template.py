from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class MessengerSendTemplateTool(BuiltinTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        recipient_id = str(tool_parameters.get("recipient_id", "")).strip()
        template_payload_raw = str(tool_parameters.get("template_payload_json", "")).strip()

        if not recipient_id:
            yield self.create_text_message("recipient_id is required")
            return
        if not template_payload_raw:
            yield self.create_text_message("template_payload_json is required")
            return

        try:
            template_payload = json.loads(template_payload_raw)
        except json.JSONDecodeError:
            yield self.create_text_message("template_payload_json must be valid JSON")
            return

        if not isinstance(template_payload, dict) or not template_payload:
            yield self.create_text_message("template_payload_json must be a non-empty JSON object")
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
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": template_payload,
                }
            },
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
            yield self.create_text_message(f"Template sent successfully. message_id={msg_id}")
        except Exception as e:
            yield self.create_text_message(f"Failed to send template: {e}")
