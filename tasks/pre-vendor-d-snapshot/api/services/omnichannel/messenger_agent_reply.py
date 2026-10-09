"""Resolve how console agent replies should be delivered on Facebook Messenger channels."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, NotRequired, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import (
    OmniChannelMessage,
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
)
from services.omnichannel.messenger_graph_send import MessengerSendDelivery

_MESSENGER_DM_INTERACTION_TYPES = frozenset(
    {
        "messenger_message",
        "postback",
        "quick_reply",
        "message",
    }
)


class MessengerAgentReplyTarget(TypedDict):
    mode: Literal["messenger", "comment"]
    recipient_psid: str
    delivery: MessengerSendDelivery
    comment_id: NotRequired[str]


class MessengerAgentReplyService:
    _STANDARD_WINDOW = timedelta(hours=24)

    @staticmethod
    def interaction_type_from_metadata(metadata: dict[str, object]) -> str:
        explicit = str(metadata.get("interaction_type") or "").strip()
        if explicit:
            return explicit
        raw_event = metadata.get("raw_event")
        if isinstance(raw_event, dict) and str(raw_event.get("item") or "") == "comment":
            return "facebook_comment"
        if isinstance(raw_event, dict) and raw_event.get("postback"):
            return "postback"
        if isinstance(raw_event, dict):
            message = raw_event.get("message")
            if isinstance(message, dict) and message.get("quick_reply"):
                return "quick_reply"
        return "messenger_message"

    @staticmethod
    def comment_id_from_message(message: OmniChannelMessage) -> str:
        metadata = dict(message.message_metadata or {})
        reply_target_id = str(metadata.get("reply_target_id") or "").strip()
        if reply_target_id:
            return reply_target_id
        external_message_id = str(message.external_message_id or "").strip()
        if external_message_id:
            return external_message_id
        raw_event = metadata.get("raw_event")
        if isinstance(raw_event, dict):
            return str(raw_event.get("comment_id") or "").strip()
        return ""

    @classmethod
    def _resolve_delivery(cls, *, last_inbound_at: datetime | None) -> MessengerSendDelivery:
        if last_inbound_at is None:
            return "human_agent"
        if datetime.utcnow() - last_inbound_at <= cls._STANDARD_WINDOW:
            return "standard"
        return "human_agent"

    @classmethod
    def _is_messenger_dm_interaction(cls, interaction_type: str) -> bool:
        return interaction_type in _MESSENGER_DM_INTERACTION_TYPES

    @classmethod
    def _find_recent_inbound_anchors(
        cls,
        session: Session,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
    ) -> tuple[OmniChannelMessage | None, OmniChannelMessage | None]:
        rows = session.scalars(
            select(OmniChannelMessage)
            .where(
                OmniChannelMessage.tenant_id == tenant_id,
                OmniChannelMessage.channel_id == channel_id,
                OmniChannelMessage.conversation_id == conversation_id,
                OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND,
                OmniChannelMessage.source != OmniChannelMessageSource.INTERNAL_NOTE,
            )
            .order_by(OmniChannelMessage.created_at.desc())
            .limit(40)
        ).all()

        latest_comment: OmniChannelMessage | None = None
        latest_messenger: OmniChannelMessage | None = None
        for row in rows:
            interaction_type = cls.interaction_type_from_metadata(dict(row.message_metadata or {}))
            if interaction_type == "facebook_comment" and latest_comment is None:
                latest_comment = row
            elif cls._is_messenger_dm_interaction(interaction_type) and latest_messenger is None:
                latest_messenger = row
            if latest_comment and latest_messenger:
                break
        return latest_comment, latest_messenger

    @classmethod
    def find_latest_comment_target(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
    ) -> MessengerAgentReplyTarget | None:
        with Session(db.engine, expire_on_commit=False) as session:
            latest_comment, latest_messenger = cls._find_recent_inbound_anchors(
                session,
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
            )
            if latest_comment is None:
                return None
            comment_id = cls.comment_id_from_message(latest_comment)
            if not comment_id:
                return None
            return {
                "mode": "comment",
                "recipient_psid": latest_comment.external_user_id,
                "comment_id": comment_id,
                "delivery": cls._resolve_delivery(last_inbound_at=latest_comment.created_at),
            }

    @classmethod
    def resolve_target(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
        external_user_id: str,
        quote_message_id: str | None = None,
    ) -> MessengerAgentReplyTarget:
        with Session(db.engine, expire_on_commit=False) as session:
            anchor: OmniChannelMessage | None = None
            if quote_message_id:
                quoted = session.scalar(
                    select(OmniChannelMessage).where(
                        OmniChannelMessage.tenant_id == tenant_id,
                        OmniChannelMessage.channel_id == channel_id,
                        OmniChannelMessage.conversation_id == conversation_id,
                        OmniChannelMessage.id == quote_message_id,
                    )
                )
                if quoted and quoted.direction == OmniChannelMessageDirection.INBOUND:
                    anchor = quoted

            latest_comment, latest_messenger = cls._find_recent_inbound_anchors(
                session,
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
            )

            if anchor is None:
                if latest_messenger and (
                    not latest_comment or latest_messenger.created_at >= latest_comment.created_at
                ):
                    anchor = latest_messenger
                elif latest_comment:
                    anchor = latest_comment
                elif latest_messenger:
                    anchor = latest_messenger

            last_inbound_at = anchor.created_at if anchor else None
            delivery = cls._resolve_delivery(last_inbound_at=last_inbound_at)

            if anchor is not None:
                interaction_type = cls.interaction_type_from_metadata(dict(anchor.message_metadata or {}))
                if interaction_type == "facebook_comment":
                    comment_id = cls.comment_id_from_message(anchor)
                    if not comment_id:
                        raise ValueError(
                            "Không xác định được bình luận Facebook để trả lời. "
                            "Hãy trả lời trực tiếp trên Facebook hoặc nhờ khách nhắn Page qua Messenger."
                        )
                    return {
                        "mode": "comment",
                        "recipient_psid": external_user_id,
                        "comment_id": comment_id,
                        "delivery": delivery,
                    }

                if (
                    latest_comment
                    and latest_messenger
                    and latest_comment.created_at > latest_messenger.created_at
                    and datetime.utcnow() - latest_messenger.created_at > cls._STANDARD_WINDOW
                ):
                    comment_id = cls.comment_id_from_message(latest_comment)
                    if comment_id:
                        return {
                            "mode": "comment",
                            "recipient_psid": external_user_id,
                            "comment_id": comment_id,
                            "delivery": cls._resolve_delivery(last_inbound_at=latest_comment.created_at),
                        }

        return {
            "mode": "messenger",
            "recipient_psid": external_user_id,
            "delivery": delivery,
        }
