import json

from services.omnichannel.omnichannel_reply_payload import OmnichannelReplyPayloadService


class TestOmnichannelReplyPayloadService:
    def test_parse_plain_text_strips_markdown(self) -> None:
        payload = OmnichannelReplyPayloadService.parse("**Hello**\n- item one")
        assert payload["type"] == "text"
        assert payload["text"] == "Hello\n• item one"

    def test_parse_cards_payload(self) -> None:
        raw = json.dumps(
            {
                "type": "cards",
                "text": "Gợi ý sản phẩm:",
                "cards": [
                    {
                        "title": "Áo khoác bomber",
                        "subtitle": "699.000đ",
                        "image_url": "https://example.com/a.jpg",
                        "buttons": [
                            {"title": "Xem chi tiết", "action": "url", "url": "https://example.com/a"}
                        ],
                    }
                ],
                "buttons": [
                    {"title": "Tìm sản phẩm", "action": "postback", "payload": "search"},
                ],
            }
        )
        payload = OmnichannelReplyPayloadService.parse(raw)
        assert payload["type"] == "cards"
        assert payload["text"] == "Gợi ý sản phẩm:"
        assert len(payload["cards"]) == 1
        assert payload["cards"][0]["title"] == "Áo khoác bomber"
        assert payload["buttons"][0]["payload"] == "search"

    def test_parse_actions_payload(self) -> None:
        raw = json.dumps(
            {
                "type": "actions",
                "text": "Bạn muốn làm gì tiếp?",
                "buttons": [
                    {"title": "Đặt tour", "action": "postback", "payload": "book_tour"},
                    {"title": "Website", "action": "url", "url": "https://example.com"},
                ],
            }
        )
        payload = OmnichannelReplyPayloadService.parse(raw)
        assert payload["type"] == "actions"
        assert len(payload["buttons"]) == 2

    def test_to_inbox_content_for_cards(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "text": "Tour Đà Nẵng",
                    "cards": [{"title": "3N2Đ", "subtitle": "5.290.000đ"}],
                    "buttons": [{"title": "Đặt ngay", "action": "postback", "payload": "book"}],
                }
            )
        )
        content = OmnichannelReplyPayloadService.to_inbox_content(payload)
        assert "Tour Đà Nẵng" in content
        assert "3N2Đ" in content
        assert "Đặt ngay" in content

    def test_legacy_quick_replies_still_supported(self) -> None:
        raw = json.dumps(
            {
                "type": "quick_replies",
                "text": "Choose",
                "quick_replies": [{"content_type": "text", "title": "A", "payload": "A"}],
            }
        )
        payload = OmnichannelReplyPayloadService.parse(raw)
        assert payload["type"] == "quick_replies"
        assert payload["quick_replies"][0]["title"] == "A"
