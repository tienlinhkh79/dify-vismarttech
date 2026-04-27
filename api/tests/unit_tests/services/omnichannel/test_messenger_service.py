import hashlib
import hmac

import pytest

from services.omnichannel.messenger_service import MessengerService


class TestVerifyWebhookHandshake:
    def test_returns_challenge_when_valid(self):
        challenge = MessengerService.verify_webhook_handshake(
            mode="subscribe",
            verify_token="token-1",
            challenge="challenge-abc",
            expected_token="token-1",
        )
        assert challenge == "challenge-abc"

    def test_raises_for_invalid_token(self):
        with pytest.raises(ValueError, match="Invalid webhook verify token"):
            MessengerService.verify_webhook_handshake(
                mode="subscribe",
                verify_token="wrong",
                challenge="challenge-abc",
                expected_token="token-1",
            )


class TestVerifyPayloadSignature:
    def test_returns_true_when_signature_matches(self):
        payload = b'{"object":"page"}'
        app_secret = "secret-123"
        digest = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        assert MessengerService.verify_payload_signature(f"sha256={digest}", payload, app_secret) is True

    def test_returns_false_when_signature_invalid(self):
        payload = b'{"object":"page"}'
        assert MessengerService.verify_payload_signature("sha256=invalid", payload, "secret-123") is False


class TestParseMessageEvents:
    def test_text_messages_are_normalized(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "user-1"},
                            "message": {"mid": "m-1", "text": "hello"},
                        },
                        {
                            "sender": {"id": "user-2"},
                            "message": {"mid": "m-2"},
                        },
                    ],
                }
            ]
        }

        events = MessengerService.parse_message_events(channel_id="channel-1", payload=payload)

        assert len(events) == 1
        assert events[0]["channel"] == "facebook_messenger"
        assert events[0]["channel_id"] == "channel-1"
        assert events[0]["external_account_id"] == "page-1"
        assert events[0]["external_user_id"] == "user-1"
        assert events[0]["text"] == "hello"
        assert events[0]["message_id"] == "m-1"

    def test_attachment_messages_are_normalized(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "user-1"},
                            "message": {
                                "mid": "m-1",
                                "attachments": [
                                    {
                                        "type": "image",
                                        "payload": {"url": "https://example.com/a.jpg"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        }

        events = MessengerService.parse_message_events(channel_id="channel-1", payload=payload)

        assert len(events) == 1
        assert events[0]["external_user_id"] == "user-1"
        assert events[0]["text"] == ""
        assert events[0]["attachments"] == [{"type": "image", "url": "https://example.com/a.jpg"}]

