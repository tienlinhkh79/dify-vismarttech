import json
from unittest.mock import MagicMock, patch

from services.omnichannel.omnichannel_reply_payload import OmnichannelReplyPayloadService
from services.omnichannel.omnichannel_reply_sender import (
    MessengerReplyAdapter,
    ZaloOaReplyAdapter,
    ZaloPersonalReplyAdapter,
)
from services.omnichannel.zalo_oa_sender import ZaloOaSender


class TestZaloOaReplyAdapter:
    def test_send_cards_builds_list_template(self) -> None:
        sender = MagicMock(spec=ZaloOaSender)
        sender.send_list_template.return_value = "msg-1"
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "text": "Sản phẩm gợi ý",
                    "cards": [
                        {
                            "title": "Áo khoác",
                            "subtitle": "699k",
                            "image_url": "https://example.com/img.jpg",
                            "buttons": [
                                {"title": "Xem", "action": "url", "url": "https://example.com/p1"}
                            ],
                        }
                    ],
                    "buttons": [
                        {"title": "Tìm thêm", "action": "postback", "payload": "search_more"},
                    ],
                }
            )
        )

        result = ZaloOaReplyAdapter.send(sender=sender, recipient_id="user-1", payload=payload)

        assert result["sent"] is True
        assert result["external_message_ids"] == ["msg-1"]
        sender.send_list_template.assert_called_once()
        args, kwargs = sender.send_list_template.call_args
        assert args[0] == "user-1"
        assert kwargs["text"] == "Sản phẩm gợi ý"
        assert kwargs["elements"][0]["title"] == "Áo khoác"
        assert kwargs["elements"][0]["default_action"]["url"] == "https://example.com/p1"
        assert kwargs["buttons"][0]["type"] == "oa.query.show"


class TestMessengerReplyAdapter:
    def test_cards_converted_to_generic_template(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "cards": [{"title": "Card 1", "subtitle": "Desc"}],
                }
            )
        )
        converted = MessengerReplyAdapter._to_messenger_payload(payload)
        assert converted["type"] == "template"
        assert converted["template_payload"]["template_type"] == "generic"
        assert converted["template_payload"]["elements"][0]["title"] == "Card 1"

    def test_actions_converted_to_quick_replies(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "actions",
                    "text": "Chọn:",
                    "buttons": [{"title": "A", "action": "postback", "payload": "A"}],
                }
            )
        )
        converted = MessengerReplyAdapter._to_messenger_payload(payload)
        assert converted["type"] == "quick_replies"
        assert converted["text"] == "Chọn:"
        assert converted["quick_replies"][0]["title"] == "A"


class TestZaloPersonalReplyAdapter:
    @patch("services.omnichannel.zalo_personal_session_service.ZaloPersonalSessionService.send_rich_message")
    @patch("services.omnichannel.zalo_personal_presence_service.ZaloPersonalPresenceService.prepare_before_send")
    def test_image_send_failure_falls_back_to_link_text(
        self,
        _prepare: MagicMock,
        send_rich: MagicMock,
    ) -> None:
        send_rich.side_effect = [
            None,
            Exception("download failed"),
            None,
        ]
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "text": "Gợi ý:",
                    "cards": [
                        {
                            "title": "Mẫu web",
                            "subtitle": "1.000.000đ",
                            "image_url": "https://vietautomate.com/broken.jpg",
                        }
                    ],
                }
            )
        )

        result = ZaloPersonalReplyAdapter.send(
            channel_id="zalo-personal-test",
            recipient_id="user-1",
            payload=payload,
        )

        assert result["sent"] is True
        assert send_rich.call_count == 3
        fallback_call = send_rich.call_args_list[2]
        assert "https://vietautomate.com/broken.jpg" in fallback_call.kwargs["text"]
        assert fallback_call.kwargs["image_urls"] == []
