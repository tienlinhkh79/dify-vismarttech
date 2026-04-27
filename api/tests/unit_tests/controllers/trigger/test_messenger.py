from unittest.mock import patch

import controllers.trigger.messenger as module


class MockRequest:
    def __init__(self, args=None, headers=None, payload_bytes=b"{}", payload_json=None):
        self.args = args or {}
        self.headers = headers or {}
        self._payload_bytes = payload_bytes
        self._payload_json = payload_json if payload_json is not None else {}

    def get_data(self, cache=False):  # noqa: ARG002
        return self._payload_bytes

    def get_json(self, silent=True):  # noqa: ARG002
        return self._payload_json


def setup_function():
    module.jsonify = lambda payload: payload


class TestVerifyMessengerWebhook:
    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", True)
    @patch.object(
        module.ChannelConfigService,
        "get_messenger_channel_config",
        return_value={"verify_token": "token-1"},
    )
    @patch.object(module.MessengerService, "verify_webhook_handshake", return_value="challenge-ok")
    def test_success(self, _mock_verify, _mock_channel):
        module.request = MockRequest(
            args={
                "hub.mode": "subscribe",
                "hub.verify_token": "token-1",
                "hub.challenge": "challenge-ok",
            }
        )

        response, status = module.verify_messenger_webhook("channel-1")
        assert status == 200
        assert response == "challenge-ok"

    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", False)
    def test_returns_404_when_disabled(self):
        module.request = MockRequest()
        response, status = module.verify_messenger_webhook("channel-1")
        assert status == 404
        assert response["error"] == "Messenger trigger is disabled"


    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", True)
    @patch.object(module.ChannelConfigService, "get_messenger_channel_config", return_value=None)
    def test_returns_404_when_channel_missing(self, _mock_channel):
        module.request = MockRequest()
        response, status = module.verify_messenger_webhook("channel-1")
        assert status == 404
        assert response["error"] == "Messenger channel not found"


class TestIngestMessengerWebhook:
    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", True)
    @patch.object(
        module.ChannelConfigService,
        "get_messenger_channel_config",
        return_value={"app_secret": "secret", "app_id": "app-1", "page_access_token": "token", "graph_api_version": "v23.0"},
    )
    @patch.object(module.MessengerService, "verify_payload_signature", return_value=True)
    @patch.object(module.MessengerService, "parse_message_events", return_value=[{"id": "evt-1"}, {"id": "evt-2"}])
    @patch.object(module.MessengerRuntimeService, "process_events", return_value=2)
    def test_accepts_valid_webhook(self, _mock_process, _mock_parse, _mock_signature, _mock_channel):
        module.request = MockRequest(
            headers={"X-Hub-Signature-256": "sha256=abc"},
            payload_bytes=b'{"object":"page"}',
            payload_json={"object": "page"},
        )

        response, status = module.ingest_messenger_webhook("channel-1")
        assert status == 200
        assert response["ok"] is True
        assert response["accepted_events"] == 2
        assert response["sent_replies"] == 2

    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", True)
    @patch.object(
        module.ChannelConfigService,
        "get_messenger_channel_config",
        return_value={"app_secret": "secret", "app_id": "app-1", "page_access_token": "token", "graph_api_version": "v23.0"},
    )
    @patch.object(module.MessengerService, "verify_payload_signature", return_value=False)
    def test_rejects_invalid_signature(self, _mock_signature, _mock_channel):
        module.request = MockRequest(
            headers={"X-Hub-Signature-256": "sha256=invalid"},
            payload_bytes=b"{}",
            payload_json={},
        )

        response, status = module.ingest_messenger_webhook("channel-1")
        assert status == 401
        assert response["error"] == "Invalid webhook signature"

    @patch.object(module.dify_config, "MESSENGER_TRIGGER_ENABLED", True)
    @patch.object(module.ChannelConfigService, "get_messenger_channel_config", return_value=None)
    def test_returns_404_when_channel_missing(self, _mock_channel):
        module.request = MockRequest()
        response, status = module.ingest_messenger_webhook("channel-1")
        assert status == 404
        assert response["error"] == "Messenger channel not found"

