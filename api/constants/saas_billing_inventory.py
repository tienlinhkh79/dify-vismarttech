"""
Inventory of billing keys used by Dify API ↔ reference Billing SaaS service.

Keep `billing_saas/plan_catalog.json` limits aligned with these keys.
FeatureService reads `/subscription/info` and `/tenant-feature-usage/info` (BillingService).
"""

from __future__ import annotations

from enum import StrEnum, auto
from typing import Final


class SubscriptionInfoKey(StrEnum):
    """Top-level keys optionally returned by GET /subscription/info (beyond enabled + subscription)."""

    MEMBERS = auto()
    APPS = auto()
    VECTOR_SPACE = auto()
    DOCUMENTS_UPLOAD_QUOTA = auto()
    ANNOTATION_QUOTA_LIMIT = auto()
    DOCS_PROCESSING = auto()
    CAN_REPLACE_LOGO = auto()
    MODEL_LOAD_BALANCING_ENABLED = auto()
    KNOWLEDGE_RATE_LIMIT = auto()
    KNOWLEDGE_PIPELINE_PUBLISH_ENABLED = auto()
    NEXT_CREDIT_RESET_DATE = auto()
    OMNICHANNEL_CHANNELS = auto()
    CRM_LEADS = auto()


QUOTA_FEATURE_TRIGGER_EVENT: Final[str] = "trigger_event"
QUOTA_FEATURE_API_RATE_LIMIT: Final[str] = "api_rate_limit"

# Fork-specific nested objects use {"limit": int}; size is derived in Dify from DB via ForkBillingUsageHelper.
OMNICHANNEL_CHANNELS_SHAPE: Final[str] = '{"limit": int} (0 = unlimited)'
CRM_LEADS_SHAPE: Final[str] = '{"limit": int} (0 = unlimited)'
