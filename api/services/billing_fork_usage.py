"""Derive fork feature usage sizes from the primary DB when billing limits are active."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelConfig, OmniChannelCrmLead


class ForkBillingUsageHelper:
    """Fills omnichannel / CRM lead sizes for FeatureModel when SaaS billing is enabled."""

    @staticmethod
    def omnichannel_channel_count(tenant_id: str) -> int:
        with Session(db.engine, expire_on_commit=False) as session:
            n = session.scalar(
                select(func.count()).select_from(OmniChannelConfig).where(OmniChannelConfig.tenant_id == tenant_id)
            )
        return int(n or 0)

    @staticmethod
    def crm_lead_count(tenant_id: str) -> int:
        with Session(db.engine, expire_on_commit=False) as session:
            n = session.scalar(
                select(func.count()).select_from(OmniChannelCrmLead).where(OmniChannelCrmLead.tenant_id == tenant_id)
            )
        return int(n or 0)

    @classmethod
    def apply_fork_usage_sizes(cls, features: Any, tenant_id: str) -> None:
        if features.omnichannel_channels.limit > 0:
            features.omnichannel_channels.size = cls.omnichannel_channel_count(tenant_id)
        if features.crm_leads.limit > 0:
            features.crm_leads.size = cls.crm_lead_count(tenant_id)
