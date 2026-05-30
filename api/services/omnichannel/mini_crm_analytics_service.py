"""Mini CRM analytics: funnel, remarketing segments, and lead timeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import sqlalchemy as sa
from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.orm import Session

from models.engine import db
from models.trigger import (
    OmniChannelConfig,
    OmniChannelConversation,
    OmniChannelCrmLead,
    OmniChannelCrmLeadActivity,
    OmniChannelCrmLeadActivityType,
    OmniChannelCrmLeadStage,
    OmniChannelType,
)
from services.omnichannel.mini_crm_service import MiniCrmService

_REMARKETING_SEGMENT_DEFINITIONS: dict[str, dict[str, str]] = {
    "stale_qualified": {
        "title_key": "miniCrm.segmentStaleQualified",
        "description_key": "miniCrm.segmentStaleQualifiedDesc",
    },
    "lost_reengage": {
        "title_key": "miniCrm.segmentLostReengage",
        "description_key": "miniCrm.segmentLostReengageDesc",
    },
    "new_unassigned": {
        "title_key": "miniCrm.segmentNewUnassigned",
        "description_key": "miniCrm.segmentNewUnassignedDesc",
    },
    "tag_vip": {
        "title_key": "miniCrm.segmentTagVip",
        "description_key": "miniCrm.segmentTagVipDesc",
    },
    "won_followup": {
        "title_key": "miniCrm.segmentWonFollowup",
        "description_key": "miniCrm.segmentWonFollowupDesc",
    },
}


class FunnelConversionRates(TypedDict):
    new_to_qualified_pct: float
    qualified_to_won_pct: float
    overall_win_pct: float


class MiniCrmAnalyticsService:
    @staticmethod
    def _log_activity(
        *,
        session: Session,
        tenant_id: str,
        conversation_id: str,
        activity_type: OmniChannelCrmLeadActivityType,
        summary: str,
        payload: dict[str, Any] | None = None,
        actor_account_id: str | None = None,
    ) -> None:
        activity = OmniChannelCrmLeadActivity(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            activity_type=activity_type,
            summary=summary[:512],
            payload=json.dumps(payload, ensure_ascii=False) if payload else None,
            actor_account_id=actor_account_id,
        )
        session.add(activity)

    @classmethod
    def log_stage_auto_qualified(cls, *, tenant_id: str, conversation_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            cls._log_activity(
                session=session,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                activity_type=OmniChannelCrmLeadActivityType.AUTO_QUALIFIED,
                summary="Auto-qualified after inbound message threshold",
                payload={"stage": OmniChannelCrmLeadStage.QUALIFIED.value},
            )
            session.commit()

    @classmethod
    def log_lead_patch_activities(
        cls,
        *,
        tenant_id: str,
        conversation_id: str,
        actor_account_id: str | None,
        before: dict[str, Any],
        after: dict[str, Any],
        notes_appended: str | None = None,
        activity_source: str | None = None,
    ) -> None:
        source_prefix = f"[{activity_source}] " if activity_source else ""
        with Session(db.engine, expire_on_commit=False) as session:
            if before.get("stage") != after.get("stage"):
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.STAGE_CHANGED,
                    summary=f"{source_prefix}Stage: {before.get('stage')} → {after.get('stage')}",
                    payload={"from": before.get("stage"), "to": after.get("stage")},
                    actor_account_id=actor_account_id,
                )
            if notes_appended:
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.NOTES_APPENDED,
                    summary=f"{source_prefix}{notes_appended[:512 - len(source_prefix)]}",
                    payload={"text": notes_appended},
                    actor_account_id=actor_account_id,
                )
            elif before.get("notes") != after.get("notes"):
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.NOTES_UPDATED,
                    summary=f"{source_prefix}Notes updated",
                    actor_account_id=actor_account_id,
                )
            if before.get("owner_account_id") != after.get("owner_account_id"):
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.OWNER_CHANGED,
                    summary="Owner assignment changed",
                    payload={
                        "from": before.get("owner_account_id"),
                        "to": after.get("owner_account_id"),
                    },
                    actor_account_id=actor_account_id,
                )
            if before.get("tags") != after.get("tags"):
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.TAGS_UPDATED,
                    summary="Tags updated",
                    payload={"from": before.get("tags"), "to": after.get("tags")},
                    actor_account_id=actor_account_id,
                )
            if before.get("source_override") != after.get("source_override"):
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.SOURCE_UPDATED,
                    summary="Source override updated",
                    actor_account_id=actor_account_id,
                )
            contact_changed = (
                before.get("contact_phone") != after.get("contact_phone")
                or before.get("contact_email") != after.get("contact_email")
            )
            if contact_changed:
                cls._log_activity(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    activity_type=OmniChannelCrmLeadActivityType.CONTACT_UPDATED,
                    summary="Contact info updated",
                    payload={
                        "phone": after.get("contact_phone"),
                        "email": after.get("contact_email"),
                    },
                    actor_account_id=actor_account_id,
                )
            session.commit()

    @classmethod
    def list_timeline(
        cls,
        *,
        tenant_id: str,
        conversation_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        normalized_limit = min(max(limit, 1), 100)
        with Session(db.engine, expire_on_commit=False) as session:
            activity_rows = list(
                session.scalars(
                    select(OmniChannelCrmLeadActivity)
                    .where(
                        OmniChannelCrmLeadActivity.tenant_id == tenant_id,
                        OmniChannelCrmLeadActivity.conversation_id == conversation_id,
                    )
                    .order_by(OmniChannelCrmLeadActivity.created_at.desc(), OmniChannelCrmLeadActivity.id.desc())
                    .limit(normalized_limit)
                ).all()
            )

        timeline_items: list[dict[str, Any]] = []
        for row in activity_rows:
            payload = None
            if row.payload:
                try:
                    payload = json.loads(row.payload)
                except json.JSONDecodeError:
                    payload = {"raw": row.payload}
            timeline_items.append(
                {
                    "kind": "activity",
                    "id": row.id,
                    "activity_type": row.activity_type.value,
                    "summary": row.summary,
                    "payload": payload,
                    "actor_account_id": row.actor_account_id,
                    "at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return {"data": timeline_items}

    @classmethod
    def get_funnel_analytics(
        cls,
        *,
        tenant_id: str,
        channel_type: str | None,
        period_days: int = 30,
    ) -> dict[str, Any]:
        normalized_days = min(max(period_days, 1), 365)
        period_start = datetime.now(UTC) - timedelta(days=normalized_days)

        with Session(db.engine, expire_on_commit=False) as session:
            stage_counts = MiniCrmService._stage_counts(
                session=session,
                tenant_id=tenant_id,
                channel_type=channel_type,
            )
            total = sum(stage_counts.values())
            new_count = stage_counts.get(OmniChannelCrmLeadStage.NEW.value, 0)
            qualified_count = stage_counts.get(OmniChannelCrmLeadStage.QUALIFIED.value, 0)
            won_count = stage_counts.get(OmniChannelCrmLeadStage.WON.value, 0)
            lost_count = stage_counts.get(OmniChannelCrmLeadStage.LOST.value, 0)

            conversation_filter = OmniChannelConversation.tenant_id == tenant_id
            if channel_type:
                try:
                    channel_type_enum = OmniChannelType(channel_type)
                    conversation_filter = and_(
                        conversation_filter, OmniChannelConversation.channel_type == channel_type_enum
                    )
                except ValueError:
                    conversation_filter = and_(
                        conversation_filter, OmniChannelConversation.channel_type == channel_type
                    )  # type: ignore[arg-type]

            recent_won = int(
                session.scalar(
                    select(func.count())
                    .select_from(OmniChannelCrmLead)
                    .join(
                        OmniChannelConversation,
                        and_(
                            OmniChannelConversation.id == OmniChannelCrmLead.conversation_id,
                            OmniChannelConversation.tenant_id == OmniChannelCrmLead.tenant_id,
                        ),
                    )
                    .where(
                        conversation_filter,
                        OmniChannelCrmLead.stage == OmniChannelCrmLeadStage.WON,
                        OmniChannelCrmLead.updated_at >= period_start,
                    )
                )
                or 0
            )
            recent_lost = int(
                session.scalar(
                    select(func.count())
                    .select_from(OmniChannelCrmLead)
                    .join(
                        OmniChannelConversation,
                        and_(
                            OmniChannelConversation.id == OmniChannelCrmLead.conversation_id,
                            OmniChannelConversation.tenant_id == OmniChannelCrmLead.tenant_id,
                        ),
                    )
                    .where(
                        conversation_filter,
                        OmniChannelCrmLead.stage == OmniChannelCrmLeadStage.LOST,
                        OmniChannelCrmLead.updated_at >= period_start,
                    )
                )
                or 0
            )

            lead_conversation_join = and_(
                OmniChannelConversation.id == OmniChannelCrmLead.conversation_id,
                OmniChannelConversation.tenant_id == OmniChannelCrmLead.tenant_id,
            )
            trend_rows = session.execute(
                select(
                    func.date(OmniChannelCrmLead.updated_at),
                    OmniChannelCrmLead.stage,
                    func.count(),
                )
                .select_from(OmniChannelCrmLead)
                .join(OmniChannelConversation, lead_conversation_join)
                .where(
                    conversation_filter,
                    OmniChannelCrmLead.updated_at >= period_start,
                    OmniChannelCrmLead.stage.in_(
                        [
                            OmniChannelCrmLeadStage.QUALIFIED,
                            OmniChannelCrmLeadStage.WON,
                            OmniChannelCrmLeadStage.LOST,
                        ]
                    ),
                )
                .group_by(func.date(OmniChannelCrmLead.updated_at), OmniChannelCrmLead.stage)
            ).all()
            daily_map: dict[str, dict[str, int]] = {}
            for day_value, stage_value, count_value in trend_rows:
                day_key = day_value.isoformat() if day_value else ""
                if not day_key:
                    continue
                if day_key not in daily_map:
                    daily_map[day_key] = {"won": 0, "lost": 0, "qualified": 0}
                stage_key = stage_value.value if hasattr(stage_value, "value") else str(stage_value)
                if stage_key in daily_map[day_key]:
                    daily_map[day_key][stage_key] = int(count_value)

            daily_pipeline: list[dict[str, Any]] = []
            cursor_day = period_start.date()
            end_day = datetime.now(UTC).date()
            while cursor_day <= end_day:
                day_key = cursor_day.isoformat()
                point = daily_map.get(day_key, {"won": 0, "lost": 0, "qualified": 0})
                daily_pipeline.append({"date": day_key, **point})
                cursor_day += timedelta(days=1)

            channel_rows = session.execute(
                select(OmniChannelConversation.channel_type, func.count())
                .select_from(OmniChannelConversation)
                .where(conversation_filter)
                .group_by(OmniChannelConversation.channel_type)
                .order_by(func.count().desc())
            ).all()
            channel_breakdown: list[dict[str, Any]] = []
            for channel_value, count_value in channel_rows:
                channel_key = channel_value.value if hasattr(channel_value, "value") else str(channel_value)
                channel_breakdown.append({"channel_type": channel_key, "count": int(count_value)})

        def _pct(numerator: int, denominator: int) -> float:
            if denominator <= 0:
                return 0.0
            return round((numerator / denominator) * 100, 1)

        conversion: FunnelConversionRates = {
            "new_to_qualified_pct": _pct(qualified_count + won_count, max(new_count + qualified_count + won_count, 1)),
            "qualified_to_won_pct": _pct(won_count, max(qualified_count + won_count, 1)),
            "overall_win_pct": _pct(won_count, max(total, 1)),
        }

        return {
            "stage_counts": stage_counts,
            "total": total,
            "period_days": normalized_days,
            "recent_won": recent_won,
            "recent_lost": recent_lost,
            "conversion": conversion,
            "funnel_steps": [
                {"stage": OmniChannelCrmLeadStage.NEW.value, "count": new_count},
                {"stage": OmniChannelCrmLeadStage.QUALIFIED.value, "count": qualified_count},
                {"stage": OmniChannelCrmLeadStage.WON.value, "count": won_count},
                {"stage": OmniChannelCrmLeadStage.LOST.value, "count": lost_count},
            ],
            "daily_pipeline": daily_pipeline,
            "channel_breakdown": channel_breakdown,
        }

    @classmethod
    def list_remarketing_segments(cls) -> dict[str, Any]:
        segments: list[dict[str, Any]] = []
        for key, meta in _REMARKETING_SEGMENT_DEFINITIONS.items():
            segments.append({"key": key, **meta})
        return {"data": segments}

    @classmethod
    def _segment_leads_query(
        cls,
        *,
        tenant_id: str,
        segment_key: str,
        channel_type: str | None,
    ):
        Conversation = OmniChannelConversation
        CrmLead = OmniChannelCrmLead
        stale_cutoff = datetime.now(UTC) - timedelta(days=7)
        followup_cutoff = datetime.now(UTC) - timedelta(days=30)

        query = (
            select(Conversation, CrmLead)
            .select_from(Conversation)
            .outerjoin(
                CrmLead,
                and_(CrmLead.conversation_id == Conversation.id, CrmLead.tenant_id == Conversation.tenant_id),
            )
            .where(Conversation.tenant_id == tenant_id)
        )

        if channel_type:
            try:
                channel_type_enum = OmniChannelType(channel_type)
                query = query.where(Conversation.channel_type == channel_type_enum)
            except ValueError:
                query = query.where(Conversation.channel_type == channel_type)  # type: ignore[arg-type]

        if segment_key == "stale_qualified":
            query = query.where(
                CrmLead.stage == OmniChannelCrmLeadStage.QUALIFIED,
                or_(
                    Conversation.last_message_at.is_(None),
                    Conversation.last_message_at < stale_cutoff,
                ),
            )
        elif segment_key == "lost_reengage":
            query = query.where(CrmLead.stage == OmniChannelCrmLeadStage.LOST)
        elif segment_key == "new_unassigned":
            query = query.where(
                or_(CrmLead.id.is_(None), CrmLead.stage == OmniChannelCrmLeadStage.NEW),
                or_(CrmLead.owner_account_id.is_(None), CrmLead.id.is_(None)),
            )
        elif segment_key == "tag_vip":
            query = query.where(
                or_(
                    func.lower(CrmLead.tags).like('%"vip"%'),
                    func.lower(CrmLead.tags).like("%vip%"),
                )
            )
        elif segment_key == "won_followup":
            query = query.where(
                CrmLead.stage == OmniChannelCrmLeadStage.WON,
                Conversation.last_message_at.is_not(None),
                Conversation.last_message_at >= followup_cutoff,
            )
        else:
            raise ValueError(f"Unknown segment: {segment_key}")

        order_timestamp = func.coalesce(Conversation.last_message_at, Conversation.created_at)
        return query.order_by(order_timestamp.desc(), Conversation.id.desc())

    @classmethod
    def get_remarketing_segment_leads(
        cls,
        *,
        tenant_id: str,
        segment_key: str,
        channel_type: str | None,
        page_offset: int | None,
        page_size: int | None,
    ) -> dict[str, Any]:
        if segment_key not in _REMARKETING_SEGMENT_DEFINITIONS:
            raise ValueError(f"Unknown segment: {segment_key}")

        normalized_offset = max(page_offset or 0, 0)
        normalized_limit = min(max(page_size or 50, 1), 200)
        lead_query = cls._segment_leads_query(
            tenant_id=tenant_id,
            segment_key=segment_key,
            channel_type=channel_type,
        )
        total_count_query = select(func.count()).select_from(lead_query.subquery())
        paged_query = lead_query.offset(normalized_offset).limit(normalized_limit)

        with Session(db.engine, expire_on_commit=False) as session:
            total = int(session.scalar(total_count_query) or 0)
            rows = list(session.execute(paged_query).all())

        response_rows: list[dict[str, Any]] = []
        with Session(db.engine, expire_on_commit=False) as session:
            for conversation_row, crm_lead_row in rows:
                channel_config_name = session.scalar(
                    select(OmniChannelConfig.name).where(
                        cast(OmniChannelConfig.tenant_id, sa.String(36)) == tenant_id,
                        OmniChannelConfig.channel_id == conversation_row.channel_id,
                    )
                )
                response_rows.append(
                    MiniCrmService._serialize_lead_row(
                        conversation_row=conversation_row,
                        crm_lead_row=crm_lead_row,
                        channel_display_name=channel_config_name,
                    )
                )

        return {
            "data": response_rows,
            "total": total,
            "offset": normalized_offset,
            "limit": normalized_limit,
            "segment_key": segment_key,
        }

    @classmethod
    def export_remarketing_segment_csv(
        cls,
        *,
        tenant_id: str,
        segment_key: str,
        channel_type: str | None,
    ) -> str:
        rows: list[dict[str, Any]] = []
        page_offset = 0
        while True:
            page = cls.get_remarketing_segment_leads(
                tenant_id=tenant_id,
                segment_key=segment_key,
                channel_type=channel_type,
                page_offset=page_offset,
                page_size=200,
            )
            batch = page.get("data") or []
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < 200:
                break
            page_offset += 200
            if page_offset >= 2000:
                break
        return cls._rows_to_csv(rows)

    @staticmethod
    def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "conversation_id",
                "contact_name",
                "phone",
                "email",
                "stage",
                "tags",
                "channel_type",
                "last_message_at",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.get("conversation_id") or "",
                    row.get("participant_display_name") or row.get("external_user_id") or "",
                    row.get("contact_phone") or "",
                    row.get("contact_email") or "",
                    row.get("stage") or "",
                    ", ".join(row.get("tags") or []),
                    row.get("channel_type") or "",
                    row.get("last_message_at") or "",
                ]
            )
        return buffer.getvalue()
