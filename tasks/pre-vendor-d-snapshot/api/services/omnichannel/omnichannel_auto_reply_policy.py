"""Shared rules for when omnichannel bot auto-reply should run."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelConfig, OmniChannelConversation, OmniChannelConversationStatus

logger = logging.getLogger(__name__)

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"


class OmnichannelAutoReplyPolicy(TypedDict):
    auto_reply_enabled: bool
    pause_when_assigned: bool
    pause_when_resolved: bool
    business_hours_enabled: bool
    business_hours_start: str
    business_hours_end: str
    timezone: str


class OmnichannelAutoReplyPolicyService:
    @staticmethod
    def from_config(config: OmniChannelConfig) -> OmnichannelAutoReplyPolicy:
        return {
            "auto_reply_enabled": bool(config.zalo_auto_reply_enabled),
            "pause_when_assigned": bool(config.auto_reply_pause_when_assigned),
            "pause_when_resolved": bool(config.auto_reply_pause_when_resolved),
            "business_hours_enabled": bool(config.auto_reply_business_hours_enabled),
            "business_hours_start": (config.auto_reply_business_hours_start or "09:00").strip() or "09:00",
            "business_hours_end": (config.auto_reply_business_hours_end or "18:00").strip() or "18:00",
            "timezone": (config.auto_reply_timezone or _DEFAULT_TIMEZONE).strip() or _DEFAULT_TIMEZONE,
        }

    @classmethod
    def load_for_channel(cls, channel_id: str) -> OmnichannelAutoReplyPolicy | None:
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(OmniChannelConfig.channel_id == channel_id)
            )
        if not config:
            return None
        return cls.from_config(config)

    @classmethod
    def should_auto_reply(
        cls,
        *,
        policy: OmnichannelAutoReplyPolicy,
        tenant_id: str,
        channel_id: str,
        external_user_id: str,
    ) -> bool:
        if not policy["auto_reply_enabled"]:
            return False
        if policy["business_hours_enabled"] and not cls._within_business_hours(policy):
            return False
        conversation = cls._load_conversation(
            tenant_id=tenant_id,
            channel_id=channel_id,
            external_user_id=external_user_id,
        )
        if conversation is None:
            return True
        if policy["pause_when_assigned"] and (conversation.assignee_account_id or "").strip():
            return False
        if policy["pause_when_resolved"] and conversation.status in (
            OmniChannelConversationStatus.RESOLVED,
            OmniChannelConversationStatus.SNOOZED,
        ):
            return False
        return True

    @staticmethod
    def _load_conversation(
        *,
        tenant_id: str,
        channel_id: str,
        external_user_id: str,
    ) -> OmniChannelConversation | None:
        with Session(db.engine, expire_on_commit=False) as session:
            return session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                    OmniChannelConversation.external_user_id == external_user_id,
                )
            )

    @classmethod
    def _within_business_hours(cls, policy: OmnichannelAutoReplyPolicy) -> bool:
        start_m = cls._parse_hhmm(policy["business_hours_start"])
        end_m = cls._parse_hhmm(policy["business_hours_end"])
        if start_m is None or end_m is None:
            return True
        try:
            tz = ZoneInfo(policy["timezone"])
        except Exception:
            logger.debug("Invalid auto-reply timezone %s", policy["timezone"], exc_info=True)
            tz = ZoneInfo(_DEFAULT_TIMEZONE)
        now_local = datetime.now(tz)
        now_m = now_local.hour * 60 + now_local.minute
        if start_m <= end_m:
            return start_m <= now_m < end_m
        return now_m >= start_m or now_m < end_m

    @staticmethod
    def _parse_hhmm(value: str) -> int | None:
        match = _TIME_RE.match((value or "").strip())
        if not match:
            return None
        return int(match.group(1)) * 60 + int(match.group(2))
