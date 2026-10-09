from unittest.mock import MagicMock, patch

import pytest

from models.trigger import OmniChannelType
from services.omnichannel.omnichannel_agent_reply_service import OmnichannelAgentReplyService


class TestOmnichannelAgentRichReply:
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelOpsService.record_message")
    @patch("services.omnichannel.omnichannel_agent_reply_service.OmnichannelReplySenderService.send_parsed")
    @patch("services.omnichannel.omnichannel_agent_reply_service.ChannelConfigService.get_meta_channel_config")
    @patch("services.omnichannel.omnichannel_agent_reply_service.fetch_page_profile", return_value={"name": "Page", "picture_url": ""})
    @patch("services.omnichannel.omnichannel_agent_reply_service.Session")
    def test_send_rich_actions_via_agent_reply(
        self,
        mock_session_cls,
        _mock_profile,
        mock_get_cfg,
        mock_send_parsed,
        mock_record,
    ) -> None:
        conv = MagicMock()
        conv.external_user_id = "psid-1"
        conv.channel_type = OmniChannelType.FACEBOOK_MESSENGER

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session.scalar.return_value = conv
        mock_session_cls.return_value = mock_session

        mock_get_cfg.return_value = {
            "tenant_id": "tenant-1",
            "app_id": "app-1",
            "page_id": "page-1",
            "page_access_token": "token",
            "graph_api_version": "v23.0",
        }
        mock_send_parsed.return_value = {
            "sent": True,
            "external_message_ids": [],
            "inbox_content": "Chọn:\n• Giày nam",
        }
        mock_record.return_value = {"id": "msg-1"}

        saved = OmnichannelAgentReplyService.send_reply(
            tenant_id="tenant-1",
            channel_id="ch-1",
            conversation_id="conv-1",
            text="",
            reply_payload={
                "type": "actions",
                "text": "Chọn:",
                "buttons": [{"title": "Giày nam", "action": "postback", "payload": "giay_nam"}],
            },
        )

        assert saved["id"] == "msg-1"
        mock_send_parsed.assert_called_once()
        assert mock_send_parsed.call_args.kwargs["channel_type"] == "facebook_messenger"

    def test_rejects_plain_text_with_reply_payload(self) -> None:
        with pytest.raises(ValueError, match="cannot be combined"):
            OmnichannelAgentReplyService.send_reply(
                tenant_id="tenant-1",
                channel_id="ch-1",
                conversation_id="conv-1",
                text="hello",
                reply_payload={"type": "actions", "text": "x", "buttons": []},
            )
