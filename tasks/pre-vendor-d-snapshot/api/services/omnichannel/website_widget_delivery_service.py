"""Deliver omnichannel agent replies back to the visitor web chat session."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.enums import ConversationFromSource, InvokeFrom, MessageStatus
from models.model import App, AppMode, Conversation, EndUser, Message
from models.trigger import OmniChannelMessage

logger = logging.getLogger(__name__)


class WebsiteWidgetDeliveryService:
    @classmethod
    def deliver_agent_text(
        cls,
        *,
        app_id: str,
        tenant_id: str,
        external_user_id: str,
        omnichannel_conversation_id: str,
        text: str,
    ) -> None:
        body = (text or "").strip()
        if not body:
            raise ValueError("Message text is required")

        web_conversation_id = cls._resolve_web_conversation_id(
            tenant_id=tenant_id,
            omnichannel_conversation_id=omnichannel_conversation_id,
        )
        if not web_conversation_id:
            raise ValueError("No linked web conversation for this visitor yet")

        with Session(db.engine, expire_on_commit=False) as session:
            app = session.scalar(select(App).where(App.id == app_id, App.tenant_id == tenant_id))
            if not app:
                raise ValueError("App not found")
            end_user = session.scalar(
                select(EndUser).where(
                    EndUser.tenant_id == tenant_id,
                    EndUser.app_id == app_id,
                    EndUser.session_id == external_user_id,
                )
            )
            if not end_user:
                end_user = session.scalar(
                    select(EndUser).where(
                        EndUser.tenant_id == tenant_id,
                        EndUser.app_id == app_id,
                        EndUser.id == external_user_id,
                    )
                )
            if not end_user:
                raise ValueError("Web visitor session not found")

            conversation = session.scalar(
                select(Conversation).where(
                    Conversation.id == web_conversation_id,
                    Conversation.app_id == app_id,
                    Conversation.from_end_user_id == end_user.id,
                )
            )
            if not conversation:
                raise ValueError("Web conversation not found for this visitor")

            last_message = session.scalar(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            parent_message_id = str(last_message.id) if last_message else None

            row = Message(
                app_id=app_id,
                model_provider=None,
                model_id="",
                override_model_configs=None,
                conversation_id=conversation.id,
                inputs={},
                query="",
                message={"type": "text", "content": body, "agent_handoff": True},
                message_tokens=0,
                message_unit_price=Decimal(0),
                message_price_unit=Decimal("0.001"),
                answer=body,
                answer_tokens=0,
                answer_unit_price=Decimal(0),
                answer_price_unit=Decimal("0.001"),
                parent_message_id=parent_message_id,
                provider_response_latency=0.0,
                total_price=Decimal(0),
                currency="USD",
                status=MessageStatus.NORMAL,
                invoke_from=InvokeFrom.TRIGGER,
                from_source=ConversationFromSource.CONSOLE,
                from_end_user_id=str(end_user.id),
                from_account_id=None,
                app_mode=AppMode.value_of(app.mode),
            )
            session.add(row)
            session.commit()

    @staticmethod
    def _resolve_web_conversation_id(*, tenant_id: str, omnichannel_conversation_id: str) -> str | None:
        with Session(db.engine, expire_on_commit=False) as session:
            rows = session.scalars(
                select(OmniChannelMessage.message_metadata)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.conversation_id == omnichannel_conversation_id,
                )
                .order_by(OmniChannelMessage.created_at.desc())
                .limit(20)
            ).all()
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            conv_id = str(raw.get("web_conversation_id") or "").strip()
            if conv_id:
                return conv_id
        return None
