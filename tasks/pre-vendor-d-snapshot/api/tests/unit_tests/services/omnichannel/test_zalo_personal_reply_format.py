import json

from services.omnichannel.omnichannel_reply_payload import OmnichannelReplyPayloadService
from services.omnichannel.zalo_personal_reply_format import ZaloPersonalReplyFormatService


class TestZaloPersonalReplyFormatService:
    def test_format_actions_as_numbered_menu(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "actions",
                    "text": "Bạn muốn xem gì?",
                    "buttons": [
                        {"title": "Giày nam", "action": "postback", "payload": "giay_nam"},
                        {"title": "Website", "action": "url", "url": "https://shop.example.com/catalog"},
                    ],
                }
            )
        )
        parts = ZaloPersonalReplyFormatService.split_payload(payload)
        assert len(parts) == 1
        text = parts[0]["text"]
        assert "Bạn muốn xem gì?" in text
        assert "1. Giày nam" in text
        assert "giay_nam" not in text
        assert "2. Website — shop.example.com/catalog" in text
        assert "Gõ số" in text

    def test_format_cards_with_image_url(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "text": "Gợi ý:",
                    "cards": [
                        {
                            "title": "Giày PJ",
                            "subtitle": "450.000đ",
                            "image_url": "https://cdn.example.com/giay.jpg",
                            "buttons": [
                                {"title": "Đặt mua", "action": "url", "url": "https://shop.example.com/p1"},
                            ],
                        }
                    ],
                }
            )
        )
        parts = ZaloPersonalReplyFormatService.split_payload(payload)
        assert len(parts) == 1
        assert parts[0]["image_urls"] == ["https://cdn.example.com/giay.jpg"]
        assert "Gợi ý:" in parts[0]["text"]
        assert "Giày PJ" in parts[0]["text"]
        assert "450.000đ" in parts[0]["text"]
        assert "shop.example.com" not in parts[0]["text"]

    def test_format_multiple_cards_adds_product_picker(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "cards": [
                        {"title": "A", "subtitle": "10k"},
                        {"title": "B", "subtitle": "20k"},
                    ],
                }
            )
        )
        parts = ZaloPersonalReplyFormatService.split_payload(payload)
        footer = parts[-1]["text"]
        assert "1. A" in footer
        assert "2. B" in footer

    def test_format_multiple_cards_one_message_per_image(self) -> None:
        payload = OmnichannelReplyPayloadService.parse(
            json.dumps(
                {
                    "type": "cards",
                    "text": "Gợi ý:",
                    "cards": [
                        {
                            "title": "A",
                            "subtitle": "10k",
                            "image_url": "https://cdn.example.com/a.jpg",
                        },
                        {
                            "title": "B",
                            "subtitle": "20k",
                            "image_url": "https://cdn.example.com/b.jpg",
                        },
                    ],
                }
            )
        )
        parts = ZaloPersonalReplyFormatService.split_payload(payload)
        assert len(parts) == 2
        assert parts[0]["image_urls"] == ["https://cdn.example.com/a.jpg"]
        assert "Gợi ý:" in parts[0]["text"]
        assert "A" in parts[0]["text"]
        assert parts[1]["image_urls"] == ["https://cdn.example.com/b.jpg"]
        assert "B" in parts[1]["text"]
        assert "Gợi ý:" not in parts[1]["text"]
