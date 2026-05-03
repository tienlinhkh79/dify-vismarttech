"""Mini CRM: lead rows scoped to omnichannel conversations (channel attribution via conversation)."""

from __future__ import annotations

import logging
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
    OmniChannelType,
)
from services.feature_service import FeatureService

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 100

_MISSING_FIELD = object()


class MiniCrmService:
    @staticmethod
    def _normalize_page_size(page_size: int | None) -> int:
        if not page_size:
            return _DEFAULT_PAGE_SIZE
        return min(max(page_size, 1), _MAX_PAGE_SIZE)

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

        response_rows: list[dict[str, Any]] = []
        for conversation_row, crm_lead_row, channel_display_name in result_rows:
            effective_lead_stage = (
                crm_lead_row.stage.value if crm_lead_row is not None else OmniChannelCrmLeadStage.NEW.value
            )
            resolved_source_label = (crm_lead_row.source_override if crm_lead_row else None) or (
                channel_display_name or conversation_row.channel_type.value
            )
            response_rows.append(
                {
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
                    "stage": effective_lead_stage,
                    "owner_account_id": crm_lead_row.owner_account_id if crm_lead_row else None,
                    "notes": crm_lead_row.notes if crm_lead_row else None,
                    "source_override": crm_lead_row.source_override if crm_lead_row else None,
                    "source_display": resolved_source_label,
                    "crm_updated_at": crm_lead_row.updated_at.isoformat() if crm_lead_row else None,
                }
            )

        return {
            "data": response_rows,
            "total": total_row_count,
            "offset": normalized_offset,
            "limit": normalized_page_size,
        }

    @classmethod
    def patch_lead(
        cls,
        *,
        tenant_id: str,
        conversation_id: str,
        stage: object = _MISSING_FIELD,
        owner_account_id: object = _MISSING_FIELD,
        notes: object = _MISSING_FIELD,
        source_override: object = _MISSING_FIELD,
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
            if source_override is not _MISSING_FIELD:
                crm_lead_row.source_override = str(source_override) if source_override else None

            session.commit()
            session.refresh(crm_lead_row)

            channel_config_name = session.scalar(
                select(OmniChannelConfig.name).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == conversation_row.channel_id,
                )
            )
        resolved_source_label = crm_lead_row.source_override or (
            channel_config_name or conversation_row.channel_type.value
        )
        return {
            "lead_id": crm_lead_row.id,
            "conversation_id": conversation_row.id,
            "channel_id": conversation_row.channel_id,
            "channel_type": conversation_row.channel_type.value,
            "channel_name": channel_config_name or "",
            "external_user_id": conversation_row.external_user_id,
            "participant_display_name": conversation_row.participant_display_name,
            "last_message_at": conversation_row.last_message_at.isoformat()
            if conversation_row.last_message_at
            else None,
            "stage": crm_lead_row.stage.value,
            "owner_account_id": crm_lead_row.owner_account_id,
            "notes": crm_lead_row.notes,
            "source_override": crm_lead_row.source_override,
            "source_display": resolved_source_label,
            "crm_updated_at": crm_lead_row.updated_at.isoformat() if crm_lead_row.updated_at else None,
        }
