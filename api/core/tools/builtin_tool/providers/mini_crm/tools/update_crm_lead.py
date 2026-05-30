from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage
from services.omnichannel.mini_crm_service import MiniCrmService


class UpdateCrmLeadTool(BuiltinTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        tenant_id = str(self.runtime.tenant_id or "").strip()
        if not tenant_id:
            yield self.create_text_message("Missing tenant context for Mini CRM tool")
            return

        target_conversation_id = str(tool_parameters.get("conversation_id") or conversation_id or "").strip()
        if not target_conversation_id:
            yield self.create_text_message("conversation_id is required")
            return

        MiniCrmService.ensure_lead_for_conversation(
            tenant_id=tenant_id,
            conversation_id=target_conversation_id,
        )

        patch_kwargs: dict[str, object] = {
            "tenant_id": tenant_id,
            "conversation_id": target_conversation_id,
            "activity_source": "workflow",
        }

        stage = tool_parameters.get("stage")
        if stage is not None and str(stage).strip():
            patch_kwargs["stage"] = str(stage).strip()

        notes_append = tool_parameters.get("notes_append")
        if notes_append is not None and str(notes_append).strip():
            patch_kwargs["notes_append"] = str(notes_append).strip()

        source_override = tool_parameters.get("source_override")
        if source_override is not None and str(source_override).strip():
            patch_kwargs["source_override"] = str(source_override).strip()

        tags = tool_parameters.get("tags")
        if tags is not None and str(tags).strip():
            patch_kwargs["tags"] = str(tags).strip()

        owner_account_id = tool_parameters.get("owner_account_id")
        if owner_account_id is not None and str(owner_account_id).strip():
            patch_kwargs["owner_account_id"] = str(owner_account_id).strip()

        contact_phone = tool_parameters.get("contact_phone")
        if contact_phone is not None and str(contact_phone).strip():
            patch_kwargs["contact_phone"] = str(contact_phone).strip()

        contact_email = tool_parameters.get("contact_email")
        if contact_email is not None and str(contact_email).strip():
            patch_kwargs["contact_email"] = str(contact_email).strip()

        if len(patch_kwargs) <= 3:
            yield self.create_text_message(
                "Provide at least one of stage, notes_append, tags, source_override, owner_account_id, "
                "contact_phone, contact_email"
            )
            return

        try:
            updated = MiniCrmService.patch_lead(**patch_kwargs)
        except ValueError as exc:
            yield self.create_text_message(f"Failed to update CRM lead: {exc}")
            return

        if not updated:
            yield self.create_text_message("Conversation not found")
            return

        yield self.create_text_message(json.dumps(updated, ensure_ascii=False))
