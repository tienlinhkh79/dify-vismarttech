from unittest.mock import MagicMock, patch

from models.trigger import OmniChannelType
from services.omnichannel.omnichannel_agent_assist_service import OmnichannelAgentAssistService
from services.omnichannel.omnichannel_typing_service import OmnichannelTypingService


class TestOmnichannelAgentAssistService:
    @patch("services.omnichannel.omnichannel_agent_assist_service.db")
    @patch("services.omnichannel.omnichannel_agent_assist_service.AppGenerateService.generate")
    @patch("services.omnichannel.omnichannel_agent_assist_service.EndUserService.get_or_create_end_user_by_type")
    @patch.object(OmnichannelAgentAssistService, "_get_reply_app")
    @patch.object(OmnichannelAgentAssistService, "_get_channel_app_id", return_value="app-1")
    @patch.object(OmnichannelAgentAssistService, "_build_transcript", return_value="Customer: hi")
    @patch("services.omnichannel.omnichannel_agent_assist_service.Session")
    def test_suggest_reply_returns_text(
        self,
        mock_session_cls: MagicMock,
        _transcript: MagicMock,
        _app_id: MagicMock,
        mock_get_app: MagicMock,
        _end_user: MagicMock,
        mock_generate: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        mock_db.engine = MagicMock()
        conv = MagicMock()
        conv.external_user_id = "psid-1"
        conv.channel_type.value = "facebook_messenger"
        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = conv
        mock_session_cls.return_value = session

        app = MagicMock()
        app.id = "app-1"
        app.tenant_id = "tenant-1"
        mock_get_app.return_value = app
        mock_generate.return_value = {"answer": "  Xin chào bạn!  "}

        result = OmnichannelAgentAssistService.suggest_reply(
            tenant_id="tenant-1",
            channel_id="messenger-1",
            conversation_id="conv-1",
        )

        assert result == {"text": "Xin chào bạn!"}


class TestOmnichannelTypingService:
    @patch("services.omnichannel.omnichannel_typing_service.db")
    @patch("services.omnichannel.omnichannel_typing_service.MessengerRuntimeService._send_sender_action")
    @patch("services.omnichannel.omnichannel_typing_service.ChannelConfigService.get_meta_channel_config")
    @patch("services.omnichannel.omnichannel_typing_service.Session")
    def test_send_typing_messenger(
        self,
        mock_session_cls: MagicMock,
        mock_cfg: MagicMock,
        mock_send: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        mock_db.engine = MagicMock()
        conv = MagicMock()
        conv.external_user_id = "psid-1"
        conv.channel_type = OmniChannelType.FACEBOOK_MESSENGER
        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = conv
        mock_session_cls.return_value = session
        mock_cfg.return_value = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }

        result = OmnichannelTypingService.send_typing(
            tenant_id="tenant-1",
            channel_id="messenger-1",
            conversation_id="conv-1",
            action="typing_on",
        )

        assert result["status"] == "sent"
        mock_send.assert_called_once()

    @patch("services.omnichannel.omnichannel_typing_service.db")
    @patch("services.omnichannel.omnichannel_typing_service.Session")
    def test_send_typing_unsupported_channel(
        self,
        mock_session_cls: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        mock_db.engine = MagicMock()
        conv = MagicMock()
        conv.channel_type = OmniChannelType.ZALO_OA
        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = conv
        mock_session_cls.return_value = session

        result = OmnichannelTypingService.send_typing(
            tenant_id="tenant-1",
            channel_id="zalo-1",
            conversation_id="conv-1",
            action="typing_on",
        )

        assert result["status"] == "unsupported"
