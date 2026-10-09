from unittest.mock import MagicMock, patch

import pytest

from models.trigger import OmniChannelType
from services.omnichannel.channel_management_service import ChannelManagementService


class TestChannelManagementSecrets:
    def test_get_channel_secrets_rejects_unknown_fields(self):
        with pytest.raises(ValueError, match="Unsupported secret fields"):
            ChannelManagementService.get_channel_secrets("tenant-1", "ch-1", ["verify_token", "bad_field"])

    @patch("services.omnichannel.channel_management_service.Session")
    def test_get_channel_secrets_returns_decrypted_values(self, mock_session_cls):
        config = MagicMock()
        config.decrypt_verify_token.return_value = " vk_plain "
        config.decrypt_app_secret.return_value = "secret_plain"
        config.decrypt_page_access_token.return_value = ""

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session.scalar.return_value = config
        mock_session_cls.return_value = mock_session

        result = ChannelManagementService.get_channel_secrets(
            "tenant-1",
            "ch-1",
            ["verify_token", "client_secret", "access_token"],
        )

        assert result == {
            "verify_token": "vk_plain",
            "client_secret": "secret_plain",
            "access_token": "",
        }

    @patch("services.omnichannel.channel_management_service.Session")
    def test_get_channel_secrets_not_found(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session.scalar.return_value = None
        mock_session_cls.return_value = mock_session

        with pytest.raises(ValueError, match="Channel not found"):
            ChannelManagementService.get_channel_secrets("tenant-1", "missing", ["verify_token"])


class TestChannelManagementOAuthStatus:
    def test_messenger_channel_exposes_connected_oauth_status(self):
        config = MagicMock()
        config.channel_type = OmniChannelType.FACEBOOK_MESSENGER
        config.id = "id-1"
        config.channel_id = "fb-1"
        config.name = "Giày PJ"
        config.app_id = "app-1"
        config.page_id = "page-1"
        config.graph_api_version = "v23.0"
        config.enabled = True
        config.created_at = None
        config.updated_at = None
        config.zalo_auto_reply_enabled = False
        config.auto_reply_pause_when_assigned = False
        config.auto_reply_pause_when_resolved = False
        config.auto_reply_business_hours_enabled = False
        config.auto_reply_business_hours_start = None
        config.auto_reply_business_hours_end = None
        config.auto_reply_timezone = None
        config.encrypted_page_access_token = "enc"
        config.oa_token_expires_at = None
        config.encrypted_oa_refresh_token = None
        config.decrypt_verify_token.return_value = "vk"
        config.decrypt_app_secret.return_value = "secret"
        config.decrypt_page_access_token.return_value = "page-token"

        row = ChannelManagementService._to_masked_dict(config)

        assert row["oauth_status"] == "connected"

    def test_messenger_channel_without_token_is_pending_auth(self):
        config = MagicMock()
        config.channel_type = OmniChannelType.FACEBOOK_MESSENGER
        config.id = "id-1"
        config.channel_id = "fb-1"
        config.name = "Giày PJ"
        config.app_id = "app-1"
        config.page_id = "page-1"
        config.graph_api_version = "v23.0"
        config.enabled = True
        config.created_at = None
        config.updated_at = None
        config.zalo_auto_reply_enabled = False
        config.auto_reply_pause_when_assigned = False
        config.auto_reply_pause_when_resolved = False
        config.auto_reply_business_hours_enabled = False
        config.auto_reply_business_hours_start = None
        config.auto_reply_business_hours_end = None
        config.auto_reply_timezone = None
        config.encrypted_page_access_token = ""
        config.oa_token_expires_at = None
        config.encrypted_oa_refresh_token = None
        config.decrypt_verify_token.return_value = "vk"
        config.decrypt_app_secret.return_value = "secret"
        config.decrypt_page_access_token.return_value = ""

        row = ChannelManagementService._to_masked_dict(config)

        assert row["oauth_status"] == "pending_auth"
