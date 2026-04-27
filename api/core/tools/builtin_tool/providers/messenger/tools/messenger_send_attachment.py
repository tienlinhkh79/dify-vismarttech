from __future__ import annotations

from collections.abc import Generator
from typing import Any

import httpx

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class MessengerSendAttachmentTool(BuiltinTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        recipient_id = str(tool_parameters.get("recipient_id", "")).strip()
        attachment_type = str(tool_parameters.get("attachment_type", "")).strip().lower()
        attachment_url = str(tool_parameters.get("attachment_url", "")).strip()

        if not recipient_id:
            yield self.create_text_message("recipient_id is required")
            return
        if attachment_type not in {"image", "video", "audio", "file"}:
            yield self.create_text_message("attachment_type must be one of: image, video, audio, file")
            return
        if not attachment_url:
            yield self.create_text_message("attachment_url is required")
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
                    "type": attachment_type,
                    "payload": {"url": attachment_url, "is_reusable": True},
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
            yield self.create_text_message(f"Attachment sent successfully. message_id={msg_id}")
        except Exception as e:
            yield self.create_text_message(f"Failed to send attachment: {e}")
