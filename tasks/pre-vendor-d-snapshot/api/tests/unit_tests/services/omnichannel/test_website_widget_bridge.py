"""Website widget omnichannel bridge and channel provisioning."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from models.trigger import OmniChannelType
from services.omnichannel.channel_management_service import ChannelManagementService
from services.omnichannel.website_widget_bridge_service import WebsiteWidgetBridgeService


def test_provision_website_widget_requires_web_app(monkeypatch: pytest.MonkeyPatch) -> None:
    app = SimpleNamespace(id="app-1", tenant_id="tenant-1", name="Pho House", enable_site=False)
    session = MagicMock()
    session.scalar.side_effect = [app, None]
    monkeypatch.setattr(
        "services.omnichannel.channel_management_service.Session",
        lambda *args, **kwargs: MagicMock(__enter__=lambda s: session, __exit__=lambda *a: None),
    )

    with pytest.raises(ValueError, match="Enable Web App"):
        ChannelManagementService.provision_website_widget_channel("tenant-1", "user-1", "app-1")


def test_record_inbound_skips_without_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    app_model = SimpleNamespace(id="app-1", tenant_id="tenant-1")
    end_user = SimpleNamespace(id="eu-1", session_id="visitor-1", name="Nam")
    monkeypatch.setattr(
        WebsiteWidgetBridgeService,
        "find_channel_for_app",
        lambda **kwargs: None,
    )
    record_mock = MagicMock()
    monkeypatch.setattr(
        "services.omnichannel.website_widget_bridge_service.OmnichannelOpsService.record_message",
        record_mock,
    )

    WebsiteWidgetBridgeService.record_inbound_user_message(
        app_model=app_model,
        end_user=end_user,
        query="tôi muốn mua phở",
        web_conversation_id="conv-1",
    )
    record_mock.assert_not_called()


def test_record_inbound_writes_message(monkeypatch: pytest.MonkeyPatch) -> None:
    app_model = SimpleNamespace(id="app-1", tenant_id="tenant-1")
    end_user = SimpleNamespace(id="eu-1", session_id="visitor-1", name="Nam")
    config = SimpleNamespace(tenant_id="tenant-1", channel_id="website-abc")
    monkeypatch.setattr(
        WebsiteWidgetBridgeService,
        "find_channel_for_app",
        lambda **kwargs: config,
    )
    record_mock = MagicMock(return_value={"id": "msg-1", "conversation_id": "omni-1"})
    monkeypatch.setattr(
        "services.omnichannel.website_widget_bridge_service.OmnichannelOpsService.record_message",
        record_mock,
    )

    WebsiteWidgetBridgeService.record_inbound_user_message(
        app_model=app_model,
        end_user=end_user,
        query="xem_quy_trinh",
        display_query="Xem quy trình",
        web_conversation_id="conv-1",
    )

    record_mock.assert_called_once()
    payload = record_mock.call_args.args[0]
    assert payload["external_user_id"] == "visitor-1"
    assert payload["content"] == "Xem quy trình"
    assert payload["metadata"]["web_conversation_id"] == "conv-1"


def test_supported_types_include_website_widget() -> None:
    assert OmniChannelType.WEBSITE_WIDGET.value in ChannelManagementService._SUPPORTED_TYPES
