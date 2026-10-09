"""Website widget agent reply delivery back to visitor web chat."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from models.enums import ConversationFromSource, InvokeFrom, MessageStatus
from services.omnichannel.website_widget_delivery_service import WebsiteWidgetDeliveryService


def test_deliver_agent_text_persists_handoff_message(monkeypatch: pytest.MonkeyPatch) -> None:
    app = SimpleNamespace(id="app-1", tenant_id="tenant-1", mode="chat")
    end_user = SimpleNamespace(id="eu-1", session_id="visitor-1")
    conversation = SimpleNamespace(id="web-conv-1")
    last_message = SimpleNamespace(id="msg-prev")
    session = MagicMock()
    session.scalar.side_effect = [app, end_user, conversation, last_message]
    captured: dict[str, object] = {}

    def fake_add(row: object) -> None:
        captured["row"] = row

    session.add.side_effect = fake_add
    monkeypatch.setattr(
        WebsiteWidgetDeliveryService,
        "_resolve_web_conversation_id",
        lambda **kwargs: "web-conv-1",
    )
    monkeypatch.setattr(
        "services.omnichannel.website_widget_delivery_service.Session",
        lambda *args, **kwargs: MagicMock(__enter__=lambda s: session, __exit__=lambda *a: None),
    )

    WebsiteWidgetDeliveryService.deliver_agent_text(
        app_id="app-1",
        tenant_id="tenant-1",
        external_user_id="visitor-1",
        omnichannel_conversation_id="omni-conv-1",
        text="Chào bạn, mình hỗ trợ nhé",
    )

    row = captured["row"]
    assert row.answer == "Chào bạn, mình hỗ trợ nhé"
    assert row.message == {
        "type": "text",
        "content": "Chào bạn, mình hỗ trợ nhé",
        "agent_handoff": True,
    }
    assert row.invoke_from == InvokeFrom.TRIGGER
    assert row.from_source == ConversationFromSource.CONSOLE
    assert row.status == MessageStatus.NORMAL
    assert row.message_unit_price == Decimal(0)
    session.commit.assert_called_once()
