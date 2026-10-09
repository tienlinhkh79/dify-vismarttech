from unittest.mock import MagicMock, patch

from models.trigger import OmniChannelType
from services.omnichannel.omnichannel_agent_reply_service import OmnichannelAgentReplyService


class TestOmnichannelAgentReplyMessengerRouting:
    @patch("services.omnichannel.omnichannel_agent_reply_service.db")
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelOpsService.record_message")
    @patch("services.omnichannel.omnichannel_agent_reply_service.MessengerRuntimeService._send_comment_reply")
    @patch("services.omnichannel.omnichannel_agent_reply_service.MessengerAgentReplyService.resolve_target")
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelAgentReplyService._meta_channel_config")
    @patch("services.omnichannel.omnichannel_agent_reply_service.Session")
    def test_send_reply_routes_facebook_comment_to_comment_api(
        self,
        mock_session_cls: MagicMock,
        mock_meta_cfg: MagicMock,
        mock_resolve_target: MagicMock,
        mock_send_comment: MagicMock,
        mock_record: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        mock_db.engine = MagicMock()
        conv = MagicMock()
        conv.external_user_id = "user-1"
        conv.channel_type = OmniChannelType.FACEBOOK_MESSENGER

        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = conv
        mock_session_cls.return_value = session

        mock_meta_cfg.return_value = (
            {
                "app_id": "app-1",
                "page_access_token": "token",
                "graph_api_version": "v23.0",
            },
            {"channel_actor_name": "Page", "channel_actor_picture_url": ""},
        )
        mock_resolve_target.return_value = {
            "mode": "comment",
            "recipient_psid": "user-1",
            "comment_id": "comment-100",
            "delivery": "standard",
        }
        mock_record.return_value = {"id": "msg-1"}

        saved = OmnichannelAgentReplyService.send_reply(
            tenant_id="tenant-1",
            channel_id="ch-1",
            conversation_id="conv-1",
            text="Xin chào bạn",
        )

        assert saved["id"] == "msg-1"
        mock_send_comment.assert_called_once_with(
            comment_id="comment-100",
            message_text="Xin chào bạn",
            channel_config={
                "app_id": "app-1",
                "page_access_token": "token",
                "graph_api_version": "v23.0",
            },
        )

    @patch("services.omnichannel.omnichannel_agent_reply_service.db")
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelOpsService.record_message")
    @patch("services.omnichannel.omnichannel_agent_reply_service.MessengerRuntimeService._send_text_reply")
    @patch("services.omnichannel.omnichannel_agent_reply_service.MessengerAgentReplyService.resolve_target")
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelAgentReplyService._meta_channel_config")
    @patch("services.omnichannel.omnichannel_agent_reply_service.Session")
    def test_send_reply_uses_standard_delivery_within_window(
        self,
        mock_session_cls: MagicMock,
        mock_meta_cfg: MagicMock,
        mock_resolve_target: MagicMock,
        mock_send_text: MagicMock,
        mock_record: MagicMock,
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

        mock_meta_cfg.return_value = (
            {
                "app_id": "app-1",
                "page_access_token": "token",
                "graph_api_version": "v23.0",
            },
            {"channel_actor_name": "Page", "channel_actor_picture_url": ""},
        )
        mock_resolve_target.return_value = {
            "mode": "messenger",
            "recipient_psid": "psid-1",
            "delivery": "standard",
        }
        mock_record.return_value = {"id": "msg-1"}

        OmnichannelAgentReplyService.send_reply(
            tenant_id="tenant-1",
            channel_id="ch-1",
            conversation_id="conv-1",
            text="Reply",
        )

        mock_send_text.assert_called_once()
        assert mock_send_text.call_args.kwargs["delivery"] == "standard"
