from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.omnichannel.messenger_runtime_service import MessengerRuntimeService


class TestMessengerRuntimeService:
    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(MessengerRuntimeService, "_generate_reply", return_value="Hello from Dify")
    @patch.object(MessengerRuntimeService, "_send_text_reply")
    def test_process_events_sends_reply(self, mock_send: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 1
        mock_send.assert_called_once_with("user-1", "Hello from Dify", channel_config)

    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(
        MessengerRuntimeService,
        "_generate_reply",
        return_value='{"type":"attachment","attachment_type":"image","url":"https://example.com/img.png"}',
    )
    @patch.object(MessengerRuntimeService, "_send_attachment_reply")
    def test_process_events_sends_attachment_reply(
        self, mock_send_attachment: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock
    ):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 1
        mock_send_attachment.assert_called_once_with(
            recipient_psid="user-1",
            attachment_type="image",
            attachment_url="https://example.com/img.png",
            channel_config=channel_config,
        )

    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(MessengerRuntimeService, "_generate_reply", return_value='{"type":"sender_action","action":"typing_on"}')
    @patch.object(MessengerRuntimeService, "_send_sender_action")
    def test_process_events_sender_action_not_counted(
        self, mock_sender_action: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock
    ):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 0
        mock_sender_action.assert_called_once_with(
            recipient_psid="user-1",
            action="typing_on",
            channel_config=channel_config,
        )

    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(
        MessengerRuntimeService,
        "_generate_reply",
        return_value='{"type":"quick_replies","text":"Choose one","quick_replies":[{"content_type":"text","title":"A","payload":"A"}]}',
    )
    @patch.object(MessengerRuntimeService, "_send_quick_replies_reply")
    def test_process_events_sends_quick_replies(
        self, mock_send_quick_replies: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock
    ):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 1
        mock_send_quick_replies.assert_called_once_with(
            recipient_psid="user-1",
            message_text="Choose one",
            quick_replies=[{"content_type": "text", "title": "A", "payload": "A"}],
            channel_config=channel_config,
        )

    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(
        MessengerRuntimeService,
        "_generate_reply",
        return_value='{"type":"template","template_payload":{"template_type":"generic","elements":[{"title":"Card 1"}]}}',
    )
    @patch.object(MessengerRuntimeService, "_send_template_reply")
    def test_process_events_sends_template(self, mock_send_template: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 1
        mock_send_template.assert_called_once_with(
            recipient_psid="user-1",
            template_payload={"template_type": "generic", "elements": [{"title": "Card 1"}]},
            channel_config=channel_config,
        )

    @patch.object(MessengerRuntimeService, "_get_reply_app", return_value=SimpleNamespace(id="app-1", tenant_id="tenant-1"))
    @patch.object(MessengerRuntimeService, "_generate_reply", return_value=None)
    @patch.object(MessengerRuntimeService, "_send_text_reply")
    def test_process_events_skips_empty_reply(
        self, mock_send: MagicMock, _mock_generate: MagicMock, _mock_get_app: MagicMock
    ):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        sent = MessengerRuntimeService.process_events(
            channel_id="ch-1",
            events=[
                {
                    "channel": "facebook_messenger",
                    "channel_id": "ch-1",
                    "external_account_id": "page-1",
                    "external_user_id": "user-1",
                    "text": "Hi",
                    "raw_event": {},
                }
            ],
            channel_config=channel_config,
        )

        assert sent == 0
        mock_send.assert_not_called()

    @patch("services.omnichannel.messenger_runtime_service.ssrf_proxy.post")
    def test_send_text_reply_calls_graph_api(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token-1",
            "graph_api_version": "v23.0",
        }

        MessengerRuntimeService._send_text_reply("user-1", "hello", channel_config)

        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch("services.omnichannel.messenger_runtime_service.ssrf_proxy.post")
    def test_send_attachment_reply_calls_graph_api(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token-1",
            "graph_api_version": "v23.0",
        }

        MessengerRuntimeService._send_attachment_reply("user-1", "image", "https://example.com/img.png", channel_config)

        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch("services.omnichannel.messenger_runtime_service.ssrf_proxy.post")
    def test_send_quick_replies_reply_calls_graph_api(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token-1",
            "graph_api_version": "v23.0",
        }

        MessengerRuntimeService._send_quick_replies_reply(
            "user-1",
            "Choose",
            [{"content_type": "text", "title": "A", "payload": "A"}],
            channel_config,
        )

        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch("services.omnichannel.messenger_runtime_service.ssrf_proxy.post")
    def test_send_template_reply_calls_graph_api(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token-1",
            "graph_api_version": "v23.0",
        }

        MessengerRuntimeService._send_template_reply(
            "user-1",
            {"template_type": "generic", "elements": [{"title": "Card 1"}]},
            channel_config,
        )

        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch.object(MessengerRuntimeService, "_send_attachment_reply")
    @patch.object(MessengerRuntimeService, "_send_text_reply")
    def test_send_reply_splits_markdown_image(self, mock_send_text: MagicMock, mock_send_attachment: MagicMock):
        channel_config = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "channel_id": "ch-1",
            "page_id": "page-1",
            "verify_token": "verify-token",
            "app_secret": "secret",
            "page_access_token": "token-1",
            "graph_api_version": "v23.0",
        }
        reply_text = "Lương: 1,100 yên/giờ\n\n![img](https://example.com/a.jpg)"

        sent = MessengerRuntimeService._send_reply("user-1", reply_text, channel_config)

        assert sent is True
        mock_send_text.assert_called_once_with("user-1", "Lương: 1,100 yên/giờ", channel_config)
        mock_send_attachment.assert_called_once_with("user-1", "image", "https://example.com/a.jpg", channel_config)

