"""Durable Zalo OA job queue (ported from zca-bridge src/store/jobQueueRepo.ts + worker.ts)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from extensions.ext_database import db
from libs.datetime_utils import naive_utc_now
from models.trigger import OmniChannelZaloJob, OmniChannelZaloJobKind, OmniChannelZaloJobStatus

logger = logging.getLogger(__name__)

_BASE_BACKOFF_SECONDS = 1
_CAP_BACKOFF_SECONDS = 300
_STALE_PROCESSING = timedelta(minutes=5)


def backoff_seconds(attempts: int) -> int:
    return min(_CAP_BACKOFF_SECONDS, _BASE_BACKOFF_SECONDS * (2**max(attempts - 1, 0)))


class ZaloBridgeJobService:
    @staticmethod
    def enqueue(
        *,
        channel_id: str,
        kind: OmniChannelZaloJobKind | str,
        dedup_key: str,
        payload: dict[str, Any],
    ) -> bool:
        kind_enum = OmniChannelZaloJobKind(kind) if isinstance(kind, str) else kind
        with Session(db.engine, expire_on_commit=False) as session:
            exists = session.scalar(
                select(OmniChannelZaloJob.id).where(
                    OmniChannelZaloJob.kind == kind_enum,
                    OmniChannelZaloJob.dedup_key == dedup_key,
                )
            )
            if exists:
                return False
            session.add(
                OmniChannelZaloJob(
                    channel_id=channel_id,
                    kind=kind_enum,
                    dedup_key=dedup_key,
                    payload=payload,
                    status=OmniChannelZaloJobStatus.PENDING,
                )
            )
            try:
                session.commit()
                return True
            except Exception:
                session.rollback()
                return False

    @classmethod
    def claim_next(cls) -> OmniChannelZaloJob | None:
        now = naive_utc_now()
        stale_before = now - _STALE_PROCESSING
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelZaloJob)
                .where(
                    OmniChannelZaloJob.next_attempt_at <= now,
                    (
                        (OmniChannelZaloJob.status == OmniChannelZaloJobStatus.PENDING)
                        | (
                            (OmniChannelZaloJob.status == OmniChannelZaloJobStatus.PROCESSING)
                            & (OmniChannelZaloJob.updated_at < stale_before)
                        )
                    ),
                )
                .order_by(OmniChannelZaloJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if not row:
                return None
            row.status = OmniChannelZaloJobStatus.PROCESSING
            row.attempts = int(row.attempts or 0) + 1
            row.updated_at = now
            session.commit()
            session.refresh(row)
            return row

    @staticmethod
    def mark_done(job_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            session.execute(
                update(OmniChannelZaloJob)
                .where(OmniChannelZaloJob.id == job_id)
                .values(status=OmniChannelZaloJobStatus.DONE, updated_at=naive_utc_now())
            )
            session.commit()

    @staticmethod
    def mark_retry(job_id: str, error: str, *, attempts: int) -> OmniChannelZaloJobStatus:
        delay = backoff_seconds(attempts)
        next_at = naive_utc_now() + timedelta(seconds=delay)
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(select(OmniChannelZaloJob).where(OmniChannelZaloJob.id == job_id))
            if not row:
                return OmniChannelZaloJobStatus.FAILED
            status = (
                OmniChannelZaloJobStatus.FAILED
                if int(row.attempts or 0) >= int(row.max_attempts or 8)
                else OmniChannelZaloJobStatus.PENDING
            )
            row.status = status
            row.last_error = (error or "")[:2000]
            row.next_attempt_at = next_at
            row.updated_at = naive_utc_now()
            session.commit()
            return status

    @staticmethod
    def list_failed(*, channel_id: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        page_size = max(1, min(limit, 200))
        with Session(db.engine, expire_on_commit=False) as session:
            query = select(OmniChannelZaloJob).where(OmniChannelZaloJob.status == OmniChannelZaloJobStatus.FAILED)
            if channel_id:
                query = query.where(OmniChannelZaloJob.channel_id == channel_id)
            rows = session.scalars(
                query.order_by(OmniChannelZaloJob.updated_at.desc()).limit(page_size)
            ).all()
        return [
            {
                "id": row.id,
                "channel_id": row.channel_id,
                "kind": str(getattr(row.kind, "value", row.kind)),
                "dedup_key": row.dedup_key,
                "attempts": int(row.attempts or 0),
                "max_attempts": int(row.max_attempts or 8),
                "last_error": row.last_error,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    @staticmethod
    def retry_failed(job_id: str) -> bool:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(select(OmniChannelZaloJob).where(OmniChannelZaloJob.id == job_id))
            if not row or row.status != OmniChannelZaloJobStatus.FAILED:
                return False
            row.status = OmniChannelZaloJobStatus.PENDING
            row.attempts = 0
            row.last_error = None
            row.next_attempt_at = naive_utc_now()
            row.updated_at = naive_utc_now()
            session.commit()
        return True
