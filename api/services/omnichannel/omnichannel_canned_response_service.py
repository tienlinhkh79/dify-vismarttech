"""Workspace canned responses for omnichannel agent composer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelCannedResponse


class OmnichannelCannedResponseService:
    @classmethod
    def list_responses(cls, *, tenant_id: str) -> list[dict[str, Any]]:
        with Session(db.engine, expire_on_commit=False) as session:
            rows = session.scalars(
                select(OmniChannelCannedResponse)
                .where(OmniChannelCannedResponse.tenant_id == tenant_id)
                .order_by(OmniChannelCannedResponse.title.asc())
            ).all()
        return [cls._to_dict(row) for row in rows]

    @classmethod
    def create_response(
        cls,
        *,
        tenant_id: str,
        title: str,
        content: str,
        shortcut: str | None = None,
    ) -> dict[str, Any]:
        title_clean = (title or "").strip()
        body = (content or "").strip()
        if not title_clean:
            raise ValueError("title is required")
        if not body:
            raise ValueError("content is required")
        with Session(db.engine, expire_on_commit=False) as session:
            row = OmniChannelCannedResponse(
                tenant_id=tenant_id,
                title=title_clean,
                content=body,
                shortcut=(shortcut or "").strip() or None,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return cls._to_dict(row)

    @classmethod
    def delete_response(cls, *, tenant_id: str, response_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelCannedResponse).where(
                    OmniChannelCannedResponse.tenant_id == tenant_id,
                    OmniChannelCannedResponse.id == response_id,
                )
            )
            if not row:
                raise ValueError("Canned response not found")
            session.delete(row)
            session.commit()

    @staticmethod
    def _to_dict(row: OmniChannelCannedResponse) -> dict[str, Any]:
        return {
            "id": row.id,
            "title": row.title,
            "content": row.content,
            "shortcut": row.shortcut,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
