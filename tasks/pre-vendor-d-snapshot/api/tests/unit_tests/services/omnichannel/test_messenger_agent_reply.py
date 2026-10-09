from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from models.trigger import OmniChannelMessageDirection
from services.omnichannel.messenger_agent_reply import MessengerAgentReplyService


class TestMessengerAgentReplyService:
    def test_interaction_type_from_comment_metadata(self) -> None:
        metadata = {
            "raw_event": {
                "item": "comment",
                "comment_id": "comment-1",
                "message": "hello",
            }
        }
        assert MessengerAgentReplyService.interaction_type_from_metadata(metadata) == "facebook_comment"

    def test_interaction_type_from_explicit_metadata(self) -> None:
        assert MessengerAgentReplyService.interaction_type_from_metadata(
            {"interaction_type": "postback"}
        ) == "postback"

    @patch("services.omnichannel.messenger_agent_reply.db")
    @patch("services.omnichannel.messenger_agent_reply.Session")
    def test_resolve_target_uses_comment_reply_for_latest_comment(
        self, mock_session_cls: MagicMock, mock_db: MagicMock
    ) -> None:
        message = MagicMock()
        message.direction = OmniChannelMessageDirection.INBOUND
        message.created_at = datetime.utcnow()
        message.external_message_id = "comment-100"
        message.message_metadata = {
            "interaction_type": "facebook_comment",
            "reply_target_id": "comment-100",
        }

        mock_db.engine = MagicMock()
        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = message
        mock_session_cls.return_value = session

        target = MessengerAgentReplyService.resolve_target(
            tenant_id="tenant-1",
            channel_id="ch-1",
            conversation_id="conv-1",
            external_user_id="user-1",
        )

        assert target["mode"] == "comment"
        assert target["comment_id"] == "comment-100"
        assert target["delivery"] == "standard"

    @patch("services.omnichannel.messenger_agent_reply.db")
    @patch("services.omnichannel.messenger_agent_reply.Session")
    def test_resolve_target_uses_human_agent_after_24h(
        self, mock_session_cls: MagicMock, mock_db: MagicMock
    ) -> None:
        message = MagicMock()
        message.direction = OmniChannelMessageDirection.INBOUND
        message.created_at = datetime.utcnow() - timedelta(hours=30)
        message.message_metadata = {"interaction_type": "messenger_message"}

        mock_db.engine = MagicMock()
        session = MagicMock()
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.scalar.return_value = message
        mock_session_cls.return_value = session

        target = MessengerAgentReplyService.resolve_target(
            tenant_id="tenant-1",
            channel_id="ch-1",
            conversation_id="conv-1",
            external_user_id="psid-1",
        )

        assert target["mode"] == "messenger"
        assert target["delivery"] == "human_agent"
