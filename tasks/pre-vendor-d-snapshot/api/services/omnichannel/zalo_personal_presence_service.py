"""Seen + typing indicators for Zalo Personal outbound replies."""

from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import (
    OmniChannelMessage,
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
)
from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService

logger = logging.getLogger(__name__)

ZALO_MESSAGE_META_KEY = "zalo_message_meta"


class ZaloPersonalPresenceOptions(TypedDict, total=False):
    skip_seen: bool
    skip_typing: bool
    skip_delay: bool
    message_meta: dict[str, Any]


class ZaloPersonalPresenceService:
    @staticmethod
    def inbound_metadata(message_meta: dict[str, Any] | None) -> dict[str, Any]:
        if isinstance(message_meta, dict) and message_meta:
            return {ZALO_MESSAGE_META_KEY: message_meta}
        return {}

    @classmethod
    def extract_message_meta(cls, metadata: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(metadata, dict):
            return None
        raw = metadata.get(ZALO_MESSAGE_META_KEY)
        return raw if isinstance(raw, dict) and raw else None

    @classmethod
    def latest_inbound_message_meta(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelMessage)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.channel_id == channel_id,
                    OmniChannelMessage.conversation_id == conversation_id,
                    OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND,
                    OmniChannelMessage.source != OmniChannelMessageSource.INTERNAL_NOTE,
                )
                .order_by(OmniChannelMessage.created_at.desc())
                .limit(1)
            )
        if not row:
            return None
        return cls.extract_message_meta(dict(row.message_metadata or {}))

    @classmethod
    def mark_seen(cls, *, channel_id: str, message_meta: dict[str, Any] | None) -> None:
        if not message_meta:
            return
        ZaloPersonalSessionService.mark_seen(channel_id=channel_id, message_meta=message_meta)

    @classmethod
    def send_typing(cls, *, channel_id: str, thread_id: str) -> None:
        ZaloPersonalSessionService.send_typing(channel_id=channel_id, thread_id=thread_id)

    @staticmethod
    def simulate_human_typing_delay(reply_text: str) -> None:
        text_length = len(reply_text.strip())
        if text_length <= 0:
            delay_seconds = 0.8
        elif text_length <= 120:
            delay_seconds = 1.2
        else:
            delay_seconds = 1.8
        time.sleep(delay_seconds)

    @classmethod
    def prepare_before_send(
        cls,
        *,
        channel_id: str,
        thread_id: str,
        reply_text: str = "",
        tenant_id: str | None = None,
        conversation_id: str | None = None,
        message_meta: dict[str, Any] | None = None,
        options: ZaloPersonalPresenceOptions | None = None,
    ) -> None:
        opts = options or {}
        if not opts.get("skip_seen"):
            meta = message_meta
            if meta is None and tenant_id and conversation_id:
                meta = cls.latest_inbound_message_meta(
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    conversation_id=conversation_id,
                )
            cls.mark_seen(channel_id=channel_id, message_meta=meta)

        if not opts.get("skip_typing"):
            cls.send_typing(channel_id=channel_id, thread_id=thread_id)

        if not opts.get("skip_delay") and reply_text.strip():
            cls.simulate_human_typing_delay(reply_text)
