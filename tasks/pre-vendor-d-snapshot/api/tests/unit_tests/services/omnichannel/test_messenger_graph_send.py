from unittest.mock import MagicMock, patch

import httpx
import pytest

from services.omnichannel.messenger_graph_send import (
    format_graph_send_error,
    is_outside_messaging_window_error,
    post_messenger_message,
)


class TestMessengerGraphSend:
    def test_is_outside_messaging_window_error(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {
            "error": {
                "message": "(#551) Người này hiện không có mặt.",
                "code": 551,
                "error_subcode": 1545041,
            }
        }
        assert is_outside_messaging_window_error(response) is True

    def test_format_graph_send_error_for_window_error(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        response.json.return_value = {
            "error": {
                "message": "(#551) Người này hiện không có mặt.",
                "code": 551,
            }
        }
        message = format_graph_send_error(response)
        assert "Facebook từ chối" in message

    @patch("services.omnichannel.messenger_graph_send.ssrf_proxy.post")
    def test_human_agent_retries_with_message_tag(self, mock_post: MagicMock) -> None:
        first = MagicMock(spec=httpx.Response)
        first.is_success = False
        first.json.return_value = {"error": {"code": 551, "message": "outside window"}}
        second = MagicMock(spec=httpx.Response)
        second.is_success = True
        mock_post.side_effect = [first, second]

        post_messenger_message(
            graph_api_version="v23.0",
            page_access_token="token",
            payload={"recipient": {"id": "psid-1"}, "message": {"text": "hi"}},
            delivery="human_agent",
        )

        assert mock_post.call_count == 2
        assert mock_post.call_args_list[0].kwargs["json"]["messaging_type"] == "RESPONSE"
        assert mock_post.call_args_list[1].kwargs["json"]["messaging_type"] == "MESSAGE_TAG"
        assert mock_post.call_args_list[1].kwargs["json"]["tag"] == "HUMAN_AGENT"

    @patch("services.omnichannel.messenger_graph_send.ssrf_proxy.post")
    def test_standard_delivery_retries_with_message_tag(self, mock_post: MagicMock) -> None:
        first = MagicMock(spec=httpx.Response)
        first.is_success = False
        first.json.return_value = {"error": {"code": 551, "message": "outside window"}}
        second = MagicMock(spec=httpx.Response)
        second.is_success = True
        mock_post.side_effect = [first, second]

        post_messenger_message(
            graph_api_version="v23.0",
            page_access_token="token",
            payload={"recipient": {"id": "psid-1"}, "message": {"text": "hi"}},
            delivery="standard",
        )

        assert mock_post.call_count == 2
        assert mock_post.call_args_list[1].kwargs["json"]["messaging_type"] == "MESSAGE_TAG"

    @patch("services.omnichannel.messenger_graph_send.ssrf_proxy.post")
    def test_standard_delivery_raises_value_error(self, mock_post: MagicMock) -> None:
        response = MagicMock(spec=httpx.Response)
        response.is_success = False
        response.status_code = 400
        response.json.return_value = {"error": {"code": 551, "message": "outside window"}}
        mock_post.return_value = response

        with pytest.raises(ValueError, match="Facebook từ chối"):
            post_messenger_message(
                graph_api_version="v23.0",
                page_access_token="token",
                payload={"recipient": {"id": "psid-1"}, "message": {"text": "hi"}},
                delivery="standard",
            )

        assert mock_post.call_count == 2
