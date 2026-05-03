"""Billing-aware limits for mini CRM lead auto-creation."""

from types import SimpleNamespace
from unittest.mock import patch

import configs
import pytest

from services.omnichannel.mini_crm_service import MiniCrmService


def test_ensure_lead_skips_when_over_crm_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    feats = SimpleNamespace(crm_leads=SimpleNamespace(size=10, limit=10))
    monkeypatch.setattr(
        "services.omnichannel.mini_crm_service.FeatureService.get_features",
        lambda _tid: feats,
    )
    monkeypatch.setattr(configs.dify_config, "BILLING_ENABLED", True)

    with patch("services.omnichannel.mini_crm_service.Session") as m_sess:
        fake_session = m_sess.return_value.__enter__.return_value
        fake_session.scalar.return_value = None
        MiniCrmService.ensure_lead_for_conversation(tenant_id="tenant-1", conversation_id="conv-1")
        fake_session.add.assert_not_called()
