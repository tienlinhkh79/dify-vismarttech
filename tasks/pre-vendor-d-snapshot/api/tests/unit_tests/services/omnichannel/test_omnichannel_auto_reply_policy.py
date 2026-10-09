"""Unit tests for omnichannel auto-reply policy."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from models.trigger import OmniChannelConversationStatus
from services.omnichannel.omnichannel_auto_reply_policy import (
    OmnichannelAutoReplyPolicy,
    OmnichannelAutoReplyPolicyService,
)


def _policy(**overrides: object) -> OmnichannelAutoReplyPolicy:
    base: OmnichannelAutoReplyPolicy = {
        "auto_reply_enabled": True,
        "pause_when_assigned": True,
        "pause_when_resolved": True,
        "business_hours_enabled": False,
        "business_hours_start": "09:00",
        "business_hours_end": "18:00",
        "timezone": "Asia/Ho_Chi_Minh",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


class TestOmnichannelAutoReplyPolicyService:
    def test_should_auto_reply_false_when_disabled(self) -> None:
        assert not OmnichannelAutoReplyPolicyService.should_auto_reply(
            policy=_policy(auto_reply_enabled=False),
            tenant_id="t1",
            channel_id="c1",
            external_user_id="u1",
        )

    @patch.object(OmnichannelAutoReplyPolicyService, "_load_conversation", return_value=None)
    def test_should_auto_reply_true_for_new_conversation(self, _mock_load: MagicMock) -> None:
        assert OmnichannelAutoReplyPolicyService.should_auto_reply(
            policy=_policy(),
            tenant_id="t1",
            channel_id="c1",
            external_user_id="u1",
        )

    @patch.object(OmnichannelAutoReplyPolicyService, "_load_conversation")
    def test_should_auto_reply_false_when_assigned(self, mock_load: MagicMock) -> None:
        mock_load.return_value = MagicMock(assignee_account_id="agent-1", status=OmniChannelConversationStatus.OPEN)
        assert not OmnichannelAutoReplyPolicyService.should_auto_reply(
            policy=_policy(pause_when_assigned=True),
            tenant_id="t1",
            channel_id="c1",
            external_user_id="u1",
        )

    @patch.object(OmnichannelAutoReplyPolicyService, "_load_conversation")
    def test_should_auto_reply_false_when_resolved(self, mock_load: MagicMock) -> None:
        mock_load.return_value = MagicMock(assignee_account_id=None, status=OmniChannelConversationStatus.RESOLVED)
        assert not OmnichannelAutoReplyPolicyService.should_auto_reply(
            policy=_policy(pause_when_resolved=True),
            tenant_id="t1",
            channel_id="c1",
            external_user_id="u1",
        )

    def test_within_business_hours_inside_window(self) -> None:
        policy = _policy(business_hours_enabled=True, business_hours_start="09:00", business_hours_end="18:00")
        with patch("services.omnichannel.omnichannel_auto_reply_policy.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 6, 8, 12, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            assert OmnichannelAutoReplyPolicyService._within_business_hours(policy)

    def test_within_business_hours_outside_window(self) -> None:
        policy = _policy(business_hours_enabled=True, business_hours_start="09:00", business_hours_end="18:00")
        with patch("services.omnichannel.omnichannel_auto_reply_policy.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 6, 8, 20, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            assert not OmnichannelAutoReplyPolicyService._within_business_hours(policy)

    def test_parse_hhmm_invalid_returns_none(self) -> None:
        assert OmnichannelAutoReplyPolicyService._parse_hhmm("25:99") is None
