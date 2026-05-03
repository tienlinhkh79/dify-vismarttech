"""Billing-aware limits for omnichannel channel creation."""

from types import SimpleNamespace
from unittest.mock import patch

import configs
import pytest

from services.omnichannel.channel_management_service import ChannelManagementService


def _payload():
    return {
        "channel_type": "facebook_messenger",
        "channel_id": "ch-1",
        "app_id": "00000000-0000-0000-0000-000000000001",
        "name": "Test",
        "external_resource_id": "page",
        "verify_token": "v",
        "access_token": "t",
        "client_secret": "s",
        "api_version": "v23.0",
        "enabled": True,
    }


def test_create_channel_rejects_at_omnichannel_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    feats = SimpleNamespace(omnichannel_channels=SimpleNamespace(size=3, limit=3))
    monkeypatch.setattr(
        "services.omnichannel.channel_management_service.FeatureService.get_features",
        lambda _tid: feats,
    )
    monkeypatch.setattr(configs.dify_config, "BILLING_ENABLED", True)

    with patch("services.omnichannel.channel_management_service.Session") as m_sess:
        fake_session = m_sess.return_value.__enter__.return_value
        fake_session.scalar.return_value = None
        with pytest.raises(ValueError, match="omnichannel channels"):
            ChannelManagementService.create_channel("tenant-1", "user-1", _payload())
