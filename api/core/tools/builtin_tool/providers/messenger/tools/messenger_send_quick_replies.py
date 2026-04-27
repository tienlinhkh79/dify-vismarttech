from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class MessengerSendQuickRepliesTool(BuiltinTool):
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
        quick_replies_raw = str(tool_parameters.get("quick_replies_json", "")).strip()

        if not recipient_id:
            yield self.create_text_message("recipient_id is required")
            return
        if not message_text:
            yield self.create_text_message("message_text is required")
            return
        if not quick_replies_raw:
            yield self.create_text_message("quick_replies_json is required")
            return

        try:
            quick_replies_data = json.loads(quick_replies_raw)
        except json.JSONDecodeError:
            yield self.create_text_message("quick_replies_json must be valid JSON")
            return

        if not isinstance(quick_replies_data, list) or not quick_replies_data:
            yield self.create_text_message("quick_replies_json must be a non-empty JSON array")
            return

        normalized_quick_replies: list[dict[str, str]] = []
        for item in quick_replies_data:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            payload = item.get("payload")
            image_url = item.get("image_url")
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(payload, str) or not payload.strip():
                continue

            normalized_item: dict[str, str] = {
                "content_type": "text",
                "title": title.strip(),
                "payload": payload.strip(),
            }
            if isinstance(image_url, str) and image_url.strip():
                normalized_item["image_url"] = image_url.strip()
            normalized_quick_replies.append(normalized_item)

        if not normalized_quick_replies:
            yield self.create_text_message("quick_replies_json has no valid quick reply items")
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
                "text": message_text,
                "quick_replies": normalized_quick_replies,
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
            yield self.create_text_message(f"Quick replies sent successfully. message_id={msg_id}")
        except Exception as e:
            yield self.create_text_message(f"Failed to send quick replies: {e}")
