"""Agent-assist helpers for the omnichannel console (AI suggest reply)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.app.entities.app_invoke_entities import InvokeFrom
from extensions.ext_database import db
from models.model import App, AppMode
from models.trigger import OmniChannelConversation, OmniChannelMessage, OmniChannelMessageSource
from services.app_generate_service import AppGenerateService
from services.end_user_service import EndUserService
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey
from services.omnichannel.omnichannel_workflow_inputs import build_workflow_start_inputs

_AGENT_ASSIST_INSTRUCTION = (
    "You are assisting a human support agent in an omnichannel inbox. "
    "Read the conversation transcript and suggest ONE concise reply the agent can send next. "
    "Match the customer's language. Output plain reply text only — no quotes, labels, or markdown fences."
)


class OmnichannelAgentAssistService:
    @staticmethod
    def _get_channel_app_id(*, tenant_id: str, channel_id: str) -> str:
        from models.trigger import OmniChannelConfig

        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.enabled.is_(True),
                )
            )
        if not config:
            raise ValueError("Channel not found")
        app_id = (config.app_id or "").strip()
        if not app_id:
            raise ValueError("Channel has no linked app; configure one in Settings → Inboxes")
        return app_id

    @staticmethod
    def _get_reply_app(app_id: str) -> App:
        with Session(db.engine, expire_on_commit=False) as session:
            app = session.scalar(select(App).where(App.id == app_id))
        if not app:
            raise ValueError("Linked app does not exist")
        app_mode = AppMode.value_of(app.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise ValueError("Linked app must be a chat-capable app")
        return app

    @classmethod
    def _build_transcript(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
        limit: int = 24,
    ) -> str:
        with Session(db.engine, expire_on_commit=False) as session:
            rows = session.scalars(
                select(OmniChannelMessage)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.channel_id == channel_id,
                    OmniChannelMessage.conversation_id == conversation_id,
                    OmniChannelMessage.source != OmniChannelMessageSource.INTERNAL_NOTE,
                )
                .order_by(OmniChannelMessage.created_at.desc())
                .limit(limit)
            ).all()
        if not rows:
            return ""
        lines: list[str] = []
        for row in reversed(rows):
            role = "Agent" if row.direction.value == "outbound" else "Customer"
            content = (row.content or "").strip()
            if not content:
                continue
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @classmethod
    def suggest_reply(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            conv = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conv:
                raise ValueError("Conversation not found")
            external_user_id = conv.external_user_id
            channel_type = conv.channel_type.value

        app_id = cls._get_channel_app_id(tenant_id=tenant_id, channel_id=channel_id)
        app = cls._get_reply_app(app_id)
        if app.tenant_id != tenant_id:
            raise ValueError("Channel not found")

        transcript = cls._build_transcript(
            tenant_id=tenant_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
        )
        if not transcript.strip():
            raise ValueError("No messages in this conversation yet")

        session_user_id = f"omnichannel-assist:{channel_id}:{external_user_id}"
        end_user = EndUserService.get_or_create_end_user_by_type(
            type=InvokeFrom.SERVICE_API,
            tenant_id=app.tenant_id,
            app_id=app.id,
            user_id=session_user_id,
        )

        query = f"{_AGENT_ASSIST_INSTRUCTION}\n\n---\nConversation:\n{transcript}\n---\nSuggested reply:"
        workflow_inputs = build_workflow_start_inputs(
            channel_id=channel_id,
            channel_type=channel_type,
            conversation_id=conversation_id,
            external_user_id=external_user_id,
        )
        workflow_inputs[OmnichannelAppStartInputKey.INTERACTION_TYPE] = "agent_assist"

        result = AppGenerateService.generate(
            app_model=app,
            user=end_user,
            args={
                "inputs": workflow_inputs,
                "query": query,
                "response_mode": "blocking",
                "auto_generate_name": False,
            },
            invoke_from=InvokeFrom.SERVICE_API,
            streaming=False,
        )

        answer = ""
        if isinstance(result, dict):
            raw = result.get("answer")
            if isinstance(raw, str):
                answer = raw.strip()
        if not answer:
            raise ValueError("App did not return a suggestion; check the linked workflow or model")
        return {"text": answer}
