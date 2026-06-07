"""Zalo message id ↔ omnichannel message id mapping (echo suppression from zca-bridge message_map)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelMessage, OmniChannelZaloMessageMap


class ZaloMessageMapService:
    @staticmethod
    def find_omnichannel_message_id(*, channel_id: str, zalo_msg_id: str) -> str | None:
        zid = (zalo_msg_id or "").strip()
        if not zid:
            return None
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelZaloMessageMap).where(
                    OmniChannelZaloMessageMap.channel_id == channel_id,
                    OmniChannelZaloMessageMap.zalo_msg_id == zid,
                )
            )
        return str(row.omnichannel_message_id) if row else None

    @staticmethod
    def find_zalo_msg_id(*, channel_id: str, omnichannel_message_id: str) -> str | None:
        mid = (omnichannel_message_id or "").strip()
        if not mid:
            return None
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelZaloMessageMap).where(
                    OmniChannelZaloMessageMap.channel_id == channel_id,
                    OmniChannelZaloMessageMap.omnichannel_message_id == mid,
                )
            )
        return str(row.zalo_msg_id) if row else None

    @staticmethod
    def record_if_new(
        *,
        channel_id: str,
        zalo_msg_id: str,
        omnichannel_message_id: str,
        direction: str,
        zalo_thread_id: str | None = None,
        quote_zalo_msg_id: str | None = None,
    ) -> bool:
        zid = (zalo_msg_id or "").strip()
        mid = (omnichannel_message_id or "").strip()
        if not zid or not mid:
            return False
        with Session(db.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(OmniChannelZaloMessageMap).where(
                    OmniChannelZaloMessageMap.channel_id == channel_id,
                    OmniChannelZaloMessageMap.zalo_msg_id == zid,
                )
            )
            if existing:
                return False
            session.add(
                OmniChannelZaloMessageMap(
                    channel_id=channel_id,
                    zalo_msg_id=zid,
                    zalo_thread_id=(zalo_thread_id or "").strip() or None,
                    omnichannel_message_id=mid,
                    direction=direction,
                    quote_zalo_msg_id=(quote_zalo_msg_id or "").strip() or None,
                )
            )
            session.commit()
        return True

    @classmethod
    def build_quote_preview(cls, *, channel_id: str, quote_zalo_msg_id: str) -> dict[str, str] | None:
        """Resolve quoted Zalo message to inbox preview for Chatwoot-style reply UI."""
        zid = (quote_zalo_msg_id or "").strip()
        if not zid:
            return None
        omni_id = cls.find_omnichannel_message_id(channel_id=channel_id, zalo_msg_id=zid)
        if not omni_id:
            return {"zalo_msg_id": zid, "content": "", "direction": "unknown"}
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(select(OmniChannelMessage).where(OmniChannelMessage.id == omni_id))
        if not row:
            return {"zalo_msg_id": zid, "content": "", "direction": "unknown"}
        return {
            "zalo_msg_id": zid,
            "omnichannel_message_id": omni_id,
            "content": (row.content or "")[:500],
            "direction": str(getattr(row.direction, "value", row.direction)),
        }
