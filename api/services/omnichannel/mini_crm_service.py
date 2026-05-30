"""Mini CRM: lead rows scoped to omnichannel conversations (channel attribution via conversation)."""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.orm import Session

from configs import dify_config
from models.engine import db
from models.trigger import (
    OmniChannelConfig,
    OmniChannelConversation,
    OmniChannelCrmLead,
    OmniChannelCrmLeadStage,
    OmniChannelMessage,
    OmniChannelMessageDirection,
    OmniChannelType,
)
from services.feature_service import FeatureService

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200
_AUTO_QUALIFY_INBOUND_THRESHOLD = 3
_MAX_TAGS = 20
_MAX_TAG_LENGTH = 64

_PHONE_PATTERN = re.compile(r"(?:\+?84|0)(?:\d[\s.-]?){8,10}\d")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

_MISSING_FIELD = object()


class MiniCrmService:
    @staticmethod
    def _normalize_page_size(page_size: int | None) -> int:
        if not page_size:
            return _DEFAULT_PAGE_SIZE
        return min(max(page_size, 1), _MAX_PAGE_SIZE)

    @staticmethod
    def _parse_tags(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        tags: list[str] = []
        for item in parsed:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if normalized and normalized not in tags:
                tags.append(normalized[:_MAX_TAG_LENGTH])
            if len(tags) >= _MAX_TAGS:
                break
        return tags

    @staticmethod
    def _serialize_tags(tags: list[str] | None) -> str | None:
        if not tags:
            return None
        normalized = [tag.strip()[:_MAX_TAG_LENGTH] for tag in tags if tag.strip()]
        if not normalized:
            return None
        return json.dumps(normalized[:_MAX_TAGS])

    @staticmethod
    def _normalize_tags_input(tags: object) -> list[str] | None:
        if tags is _MISSING_FIELD:
            return None
        if tags is None:
            return []
        if isinstance(tags, str):
            parts = [part.strip() for part in tags.replace(";", ",").split(",")]
            return [part[:_MAX_TAG_LENGTH] for part in parts if part][:_MAX_TAGS]
        if isinstance(tags, list):
            result: list[str] = []
            for item in tags:
                if not isinstance(item, str):
                    continue
                normalized = item.strip()
                if normalized and normalized not in result:
                    result.append(normalized[:_MAX_TAG_LENGTH])
                if len(result) >= _MAX_TAGS:
                    break
            return result
        raise ValueError("Invalid tags payload")

    @classmethod
    def _extract_contacts_from_text(cls, text: str) -> tuple[str | None, str | None]:
        phone_match = _PHONE_PATTERN.search(text)
        email_match = _EMAIL_PATTERN.search(text)
        phone = re.sub(r"[\s.-]", "", phone_match.group(0)) if phone_match else None
        email = email_match.group(0).lower() if email_match else None
        return phone, email

    @classmethod
    def _maybe_extract_and_persist_contacts(
        cls,
        *,
        session: Session,
        tenant_id: str,
        conversation_id: str,
        crm_lead_row: OmniChannelCrmLead | None,
    ) -> None:
        if crm_lead_row is None:
            return
        if crm_lead_row.contact_phone and crm_lead_row.contact_email:
            return
        messages = list(
            session.scalars(
                select(OmniChannelMessage.content)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.conversation_id == conversation_id,
                    OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND,
                )
                .order_by(OmniChannelMessage.created_at.desc(), OmniChannelMessage.id.desc())
                .limit(20)
            ).all()
        )
        combined_text = "\n".join(content for content in messages if content)
        if not combined_text.strip():
            return
        phone, email = cls._extract_contacts_from_text(combined_text)
        changed = False
        if phone and not crm_lead_row.contact_phone:
            crm_lead_row.contact_phone = phone[:32]
            changed = True
        if email and not crm_lead_row.contact_email:
            crm_lead_row.contact_email = email[:320]
            changed = True
        if changed:
            session.add(crm_lead_row)

    @classmethod
    def maybe_auto_qualify_from_inbound(cls, *, tenant_id: str, conversation_id: str) -> None:
        if _AUTO_QUALIFY_INBOUND_THRESHOLD <= 0:
            return
        with Session(db.engine, expire_on_commit=False) as session:
            crm_lead_row = session.scalar(
                select(OmniChannelCrmLead).where(
                    OmniChannelCrmLead.tenant_id == tenant_id,
                    OmniChannelCrmLead.conversation_id == conversation_id,
                )
            )
            if crm_lead_row is None or crm_lead_row.stage != OmniChannelCrmLeadStage.NEW:
                return
            inbound_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(OmniChannelMessage)
                    .where(
                        OmniChannelMessage.tenant_id == tenant_id,
                        OmniChannelMessage.conversation_id == conversation_id,
                        OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND,
                    )
                )
                or 0
            )
            if inbound_count < _AUTO_QUALIFY_INBOUND_THRESHOLD:
                return
            crm_lead_row.stage = OmniChannelCrmLeadStage.QUALIFIED
            session.add(crm_lead_row)
            session.commit()
        from services.omnichannel.mini_crm_analytics_service import MiniCrmAnalyticsService

        MiniCrmAnalyticsService.log_stage_auto_qualified(tenant_id=tenant_id, conversation_id=conversation_id)

    @classmethod
    def ensure_lead_for_conversation(cls, *, tenant_id: str, conversation_id: str) -> None:
        """Create a CRM lead row if missing (idempotent)."""
        with Session(db.engine, expire_on_commit=False) as session:
            exists = session.scalar(
                select(OmniChannelCrmLead.id).where(
                    OmniChannelCrmLead.tenant_id == tenant_id,
                    OmniChannelCrmLead.conversation_id == conversation_id,
                )
            )
            if exists:
                return

            if dify_config.BILLING_ENABLED:
                feats = FeatureService.get_features(tenant_id)
                leads = feats.crm_leads
                if 0 < leads.limit <= leads.size:
                    logger.info(
                        "ensure_lead_for_conversation skipped: CRM lead limit reached tenant=%s",
                        tenant_id,
                    )
                    return

            new_lead = OmniChannelCrmLead(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                stage=OmniChannelCrmLeadStage.NEW,
            )
            session.add(new_lead)
            try:
                session.commit()
            except Exception:
                session.rollback()
                logger.debug(
                    "ensure_lead_for_conversation race or failure tenant=%s conversation=%s",
                    tenant_id,
                    conversation_id,
                    exc_info=True,
                )

    @classmethod
    def list_leads(
        cls,
        *,
        tenant_id: str,
        channel_type: str | None,
        stage: str | None,
        search_query: str | None,
        page_offset: int | None,
        page_size: int | None,
    ) -> dict[str, Any]:
        Conversation = OmniChannelConversation
        CrmLead = OmniChannelCrmLead
        ChannelConfig = OmniChannelConfig

        normalized_page_size = cls._normalize_page_size(page_size)
        normalized_offset = max(page_offset or 0, 0)

        lead_list_query = (
            select(Conversation, CrmLead, ChannelConfig.name)
            .select_from(Conversation)
            .outerjoin(
                CrmLead,
                and_(CrmLead.conversation_id == Conversation.id, CrmLead.tenant_id == Conversation.tenant_id),
            )
            .outerjoin(
                ChannelConfig,
                and_(
                    ChannelConfig.channel_id == Conversation.channel_id,
                    # configs.tenant_id is UUID in PostgreSQL; conversations.tenant_id is varchar(36).
                    cast(ChannelConfig.tenant_id, sa.String(36)) == Conversation.tenant_id,
                ),
            )
            .where(Conversation.tenant_id == tenant_id)
        )

        if channel_type:
            try:
                channel_type_enum = OmniChannelType(channel_type)
                lead_list_query = lead_list_query.where(Conversation.channel_type == channel_type_enum)
            except ValueError:
                lead_list_query = lead_list_query.where(Conversation.channel_type == channel_type)  # type: ignore[arg-type]

        if stage:
            try:
                stage_enum = OmniChannelCrmLeadStage(stage)
                if stage_enum == OmniChannelCrmLeadStage.NEW:
                    lead_list_query = lead_list_query.where(
                        or_(CrmLead.id.is_(None), CrmLead.stage == OmniChannelCrmLeadStage.NEW)
                    )
                else:
                    lead_list_query = lead_list_query.where(CrmLead.stage == stage_enum)
            except ValueError:
                lead_list_query = lead_list_query.where(CrmLead.stage == stage)  # type: ignore[arg-type]

        if search_query and search_query.strip():
            search_pattern = f"%{search_query.strip().lower()}%"
            lead_list_query = lead_list_query.where(
                or_(
                    func.lower(Conversation.participant_display_name).like(search_pattern),
                    func.lower(Conversation.external_user_id).like(search_pattern),
                    func.lower(CrmLead.notes).like(search_pattern),
                    func.lower(CrmLead.tags).like(search_pattern),
                    func.lower(CrmLead.contact_phone).like(search_pattern),
                    func.lower(CrmLead.contact_email).like(search_pattern),
                    func.lower(CrmLead.source_override).like(search_pattern),
                )
            )

        total_count_query = select(func.count()).select_from(lead_list_query.subquery())
        order_timestamp = func.coalesce(Conversation.last_message_at, Conversation.created_at)
        lead_list_query = (
            lead_list_query.order_by(order_timestamp.desc(), Conversation.id.desc())
            .offset(normalized_offset)
            .limit(normalized_page_size)
        )

        with Session(db.engine, expire_on_commit=False) as session:
            total_row_count = int(session.scalar(total_count_query) or 0)
            result_rows = list(session.execute(lead_list_query).all())
            stage_counts = cls._stage_counts(session=session, tenant_id=tenant_id, channel_type=channel_type)
            for conversation_row, crm_lead_row, _channel_display_name in result_rows:
                cls._maybe_extract_and_persist_contacts(
                    session=session,
                    tenant_id=tenant_id,
                    conversation_id=conversation_row.id,
                    crm_lead_row=crm_lead_row,
                )
            session.commit()
            response_rows = [
                cls._serialize_lead_row(
                    conversation_row=conversation_row,
                    crm_lead_row=crm_lead_row,
                    channel_display_name=channel_display_name,
                )
                for conversation_row, crm_lead_row, channel_display_name in result_rows
            ]

        page_number = (normalized_offset // normalized_page_size) + 1 if normalized_page_size else 1
        total_pages = (
            max((total_row_count + normalized_page_size - 1) // normalized_page_size, 1)
            if normalized_page_size
            else 1
        )

        return {
            "data": response_rows,
            "total": total_row_count,
            "offset": normalized_offset,
            "limit": normalized_page_size,
            "page": page_number,
            "page_size": normalized_page_size,
            "total_pages": total_pages,
            "has_next": page_number < total_pages,
            "has_prev": page_number > 1,
            "stage_counts": stage_counts,
        }

    @classmethod
    def _stage_counts(
        cls,
        *,
        session: Session,
        tenant_id: str,
        channel_type: str | None,
    ) -> dict[str, int]:
        Conversation = OmniChannelConversation
        CrmLead = OmniChannelCrmLead

        conversation_filter = Conversation.tenant_id == tenant_id
        if channel_type:
            try:
                channel_type_enum = OmniChannelType(channel_type)
                conversation_filter = and_(conversation_filter, Conversation.channel_type == channel_type_enum)
            except ValueError:
                conversation_filter = and_(conversation_filter, Conversation.channel_type == channel_type)  # type: ignore[arg-type]

        total_conversations = int(
            session.scalar(select(func.count()).select_from(Conversation).where(conversation_filter)) or 0
        )

        def _count_stage(stage_enum: OmniChannelCrmLeadStage) -> int:
            count_query = (
                select(func.count())
                .select_from(CrmLead)
                .join(
                    Conversation,
                    and_(Conversation.id == CrmLead.conversation_id, Conversation.tenant_id == CrmLead.tenant_id),
                )
                .where(conversation_filter, CrmLead.stage == stage_enum)
            )
            return int(session.scalar(count_query) or 0)

        qualified_count = _count_stage(OmniChannelCrmLeadStage.QUALIFIED)
        won_count = _count_stage(OmniChannelCrmLeadStage.WON)
        lost_count = _count_stage(OmniChannelCrmLeadStage.LOST)
        new_count = max(total_conversations - qualified_count - won_count - lost_count, 0)

        return {
            OmniChannelCrmLeadStage.NEW.value: new_count,
            OmniChannelCrmLeadStage.QUALIFIED.value: qualified_count,
            OmniChannelCrmLeadStage.WON.value: won_count,
            OmniChannelCrmLeadStage.LOST.value: lost_count,
        }

    @classmethod
    def _serialize_lead_row(
        cls,
        *,
        conversation_row: OmniChannelConversation,
        crm_lead_row: OmniChannelCrmLead | None,
        channel_display_name: str | None,
    ) -> dict[str, Any]:
        effective_lead_stage = (
            crm_lead_row.stage.value if crm_lead_row is not None else OmniChannelCrmLeadStage.NEW.value
        )
        resolved_source_label = (crm_lead_row.source_override if crm_lead_row else None) or (
            channel_display_name or conversation_row.channel_type.value
        )
        return {
            "lead_id": crm_lead_row.id if crm_lead_row else None,
            "conversation_id": conversation_row.id,
            "channel_id": conversation_row.channel_id,
            "channel_type": conversation_row.channel_type.value,
            "channel_name": channel_display_name or "",
            "external_user_id": conversation_row.external_user_id,
            "participant_display_name": conversation_row.participant_display_name,
            "last_message_at": conversation_row.last_message_at.isoformat()
            if conversation_row.last_message_at
            else None,
            "last_message_preview": conversation_row.last_message_preview,
            "stage": effective_lead_stage,
            "owner_account_id": crm_lead_row.owner_account_id if crm_lead_row else None,
            "notes": crm_lead_row.notes if crm_lead_row else None,
            "source_override": crm_lead_row.source_override if crm_lead_row else None,
            "source_display": resolved_source_label,
            "tags": cls._parse_tags(crm_lead_row.tags if crm_lead_row else None),
            "contact_phone": crm_lead_row.contact_phone if crm_lead_row else None,
            "contact_email": crm_lead_row.contact_email if crm_lead_row else None,
            "crm_updated_at": crm_lead_row.updated_at.isoformat() if crm_lead_row and crm_lead_row.updated_at else None,
        }

    @classmethod
    def get_lead(cls, *, tenant_id: str, conversation_id: str) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            conversation_row = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conversation_row:
                return None

            crm_lead_row = session.scalar(
                select(OmniChannelCrmLead).where(
                    OmniChannelCrmLead.tenant_id == tenant_id,
                    OmniChannelCrmLead.conversation_id == conversation_id,
                )
            )
            cls._maybe_extract_and_persist_contacts(
                session=session,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                crm_lead_row=crm_lead_row,
            )
            if crm_lead_row:
                session.commit()
                session.refresh(crm_lead_row)
            channel_config_name = session.scalar(
                select(OmniChannelConfig.name).where(
                    cast(OmniChannelConfig.tenant_id, sa.String(36)) == tenant_id,
                    OmniChannelConfig.channel_id == conversation_row.channel_id,
                )
            )
        return cls._serialize_lead_row(
            conversation_row=conversation_row,
            crm_lead_row=crm_lead_row,
            channel_display_name=channel_config_name,
        )

    @classmethod
    def patch_lead(
        cls,
        *,
        tenant_id: str,
        conversation_id: str,
        stage: object = _MISSING_FIELD,
        owner_account_id: object = _MISSING_FIELD,
        notes: object = _MISSING_FIELD,
        notes_append: object = _MISSING_FIELD,
        source_override: object = _MISSING_FIELD,
        tags: object = _MISSING_FIELD,
        contact_phone: object = _MISSING_FIELD,
        contact_email: object = _MISSING_FIELD,
        actor_account_id: object = _MISSING_FIELD,
        activity_source: object = _MISSING_FIELD,
    ) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            conversation_row = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conversation_row:
                return {}

            crm_lead_row = session.scalar(
                select(OmniChannelCrmLead).where(
                    OmniChannelCrmLead.tenant_id == tenant_id,
                    OmniChannelCrmLead.conversation_id == conversation_id,
                )
            )
            before_state: dict[str, Any] = {
                "stage": crm_lead_row.stage.value if crm_lead_row else OmniChannelCrmLeadStage.NEW.value,
                "owner_account_id": crm_lead_row.owner_account_id if crm_lead_row else None,
                "notes": crm_lead_row.notes if crm_lead_row else None,
                "source_override": crm_lead_row.source_override if crm_lead_row else None,
                "tags": cls._parse_tags(crm_lead_row.tags if crm_lead_row else None),
                "contact_phone": crm_lead_row.contact_phone if crm_lead_row else None,
                "contact_email": crm_lead_row.contact_email if crm_lead_row else None,
            }
            notes_append_value: str | None = None

            if crm_lead_row is None:
                crm_lead_row = OmniChannelCrmLead(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    stage=OmniChannelCrmLeadStage.NEW,
                )
                session.add(crm_lead_row)
                session.flush()

            if stage is not _MISSING_FIELD:
                crm_lead_row.stage = OmniChannelCrmLeadStage(str(stage))
            if owner_account_id is not _MISSING_FIELD:
                crm_lead_row.owner_account_id = (str(owner_account_id) if owner_account_id else None)
            if notes is not _MISSING_FIELD:
                crm_lead_row.notes = str(notes) if notes is not None else None
            if notes_append is not _MISSING_FIELD and notes_append:
                snippet = str(notes_append).strip()
                if snippet:
                    notes_append_value = snippet
                    prev = (crm_lead_row.notes or "").strip()
                    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
                    line = f"[{stamp}] {snippet}"
                    crm_lead_row.notes = f"{prev}\n{line}".strip() if prev else line
            if source_override is not _MISSING_FIELD:
                crm_lead_row.source_override = str(source_override) if source_override else None
            if tags is not _MISSING_FIELD:
                normalized_tags = cls._normalize_tags_input(tags)
                crm_lead_row.tags = cls._serialize_tags(normalized_tags)
            if contact_phone is not _MISSING_FIELD:
                crm_lead_row.contact_phone = str(contact_phone)[:32] if contact_phone else None
            if contact_email is not _MISSING_FIELD:
                crm_lead_row.contact_email = str(contact_email)[:320] if contact_email else None

            session.commit()
            session.refresh(crm_lead_row)

            channel_config_name = session.scalar(
                select(OmniChannelConfig.name).where(
                    cast(OmniChannelConfig.tenant_id, sa.String(36)) == tenant_id,
                    OmniChannelConfig.channel_id == conversation_row.channel_id,
                )
            )
            after_state: dict[str, Any] = {
                "stage": crm_lead_row.stage.value,
                "owner_account_id": crm_lead_row.owner_account_id,
                "notes": crm_lead_row.notes,
                "source_override": crm_lead_row.source_override,
                "tags": cls._parse_tags(crm_lead_row.tags),
                "contact_phone": crm_lead_row.contact_phone,
                "contact_email": crm_lead_row.contact_email,
            }
        from services.omnichannel.mini_crm_analytics_service import MiniCrmAnalyticsService

        resolved_actor = None
        if actor_account_id is not _MISSING_FIELD and actor_account_id:
            resolved_actor = str(actor_account_id)
        resolved_activity_source = None
        if activity_source is not _MISSING_FIELD and activity_source:
            resolved_activity_source = str(activity_source).strip() or None
        MiniCrmAnalyticsService.log_lead_patch_activities(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            actor_account_id=resolved_actor,
            before=before_state,
            after=after_state,
            notes_appended=notes_append_value,
            activity_source=resolved_activity_source,
        )
        return cls._serialize_lead_row(
            conversation_row=conversation_row,
            crm_lead_row=crm_lead_row,
            channel_display_name=channel_config_name,
        )

    @classmethod
    def bulk_patch_leads(
        cls,
        *,
        tenant_id: str,
        conversation_ids: list[str],
        stage: object = _MISSING_FIELD,
        owner_account_id: object = _MISSING_FIELD,
        tags: object = _MISSING_FIELD,
    ) -> dict[str, Any]:
        unique_ids = [conversation_id for conversation_id in dict.fromkeys(conversation_ids) if conversation_id.strip()]
        updated_rows: list[dict[str, Any]] = []
        for conversation_id in unique_ids[:200]:
            patched = cls.patch_lead(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                stage=stage,
                owner_account_id=owner_account_id,
                tags=tags,
            )
            if patched:
                updated_rows.append(patched)
        return {"data": updated_rows, "count": len(updated_rows)}

    @classmethod
    def export_leads_csv(
        cls,
        *,
        tenant_id: str,
        channel_type: str | None,
        stage: str | None,
        search_query: str | None,
    ) -> str:
        rows: list[dict[str, Any]] = []
        page_offset = 0
        while True:
            page = cls.list_leads(
                tenant_id=tenant_id,
                channel_type=channel_type,
                stage=stage,
                search_query=search_query,
                page_offset=page_offset,
                page_size=_MAX_PAGE_SIZE,
            )
            batch = page.get("data") or []
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < _MAX_PAGE_SIZE:
                break
            page_offset += _MAX_PAGE_SIZE
            if page_offset >= 2000:
                break

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "conversation_id",
                "contact_name",
                "external_user_id",
                "phone",
                "email",
                "channel_type",
                "channel_name",
                "source",
                "stage",
                "owner_account_id",
                "tags",
                "notes",
                "crm_updated_at",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.get("conversation_id") or "",
                    row.get("participant_display_name") or "",
                    row.get("external_user_id") or "",
                    row.get("contact_phone") or "",
                    row.get("contact_email") or "",
                    row.get("channel_type") or "",
                    row.get("channel_name") or "",
                    row.get("source_display") or "",
                    row.get("stage") or "",
                    row.get("owner_account_id") or "",
                    ", ".join(row.get("tags") or []),
                    row.get("notes") or "",
                    row.get("crm_updated_at") or "",
                ]
            )
        return buffer.getvalue()
