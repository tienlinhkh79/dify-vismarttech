from unittest.mock import MagicMock, patch

from services.omnichannel.messenger_graph_profile import (
    extract_graph_picture_url,
    fetch_messenger_user_profile,
    fetch_page_profile,
)


class TestExtractGraphPictureUrl:
    def test_nested_data_url(self) -> None:
        assert (
            extract_graph_picture_url({"data": {"url": "https://cdn.example/p.png"}})
            == "https://cdn.example/p.png"
        )

    def test_top_level_url(self) -> None:
        assert extract_graph_picture_url({"url": "https://cdn.example/q.jpg"}) == "https://cdn.example/q.jpg"

    def test_non_dict_returns_empty(self) -> None:
        assert extract_graph_picture_url(None) == ""
        assert extract_graph_picture_url("x") == ""


class TestFetchMessengerUserProfile:
    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_returns_profile_pic_on_success(self, mock_proxy: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "name": "Alex",
            "profile_pic": "https://platform-lookaside.fbsbx.com/pic",
        }
        mock_proxy.get.return_value = mock_resp

        out = fetch_messenger_user_profile(psid="123", access_token="tok", graph_version="v23.0")

        assert out == {"name": "Alex", "profile_pic": "https://platform-lookaside.fbsbx.com/pic"}
        mock_proxy.get.assert_called_once()
        args, kwargs = mock_proxy.get.call_args
        assert "graph.facebook.com/v23.0/123" in args[0]
        assert kwargs["params"]["fields"] == "name,first_name,last_name,profile_pic,picture"

    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_fills_picture_from_picture_edge(self, mock_proxy: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "first_name": "Bo",
            "last_name": "",
            "picture": {"data": {"url": "https://from-picture-edge"}},
        }
        mock_proxy.get.return_value = mock_resp

        out = fetch_messenger_user_profile(psid="99", access_token="tok", graph_version="v23.0")

        assert out["name"] == "Bo"
        assert out["profile_pic"] == "https://from-picture-edge"

    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_http_error_returns_empty(self, mock_proxy: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = '{"error":{"message":"Invalid OAuth access token"}}'
        mock_proxy.get.return_value = mock_resp

        out = fetch_messenger_user_profile(psid="1", access_token="bad", graph_version="v23.0")

        assert out == {"name": "", "profile_pic": ""}

    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_empty_object_returns_empty(self, mock_proxy: MagicMock) -> None:
        """Meta returns {} when profile fields are not available (BAUPA / opt-in / policy)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_proxy.get.return_value = mock_resp

        out = fetch_messenger_user_profile(psid="2", access_token="tok", graph_version="v23.0")

        assert out == {"name": "", "profile_pic": ""}

    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_error_payload_returns_empty(self, mock_proxy: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": {"message": "No profile", "code": 2018218}}
        mock_proxy.get.return_value = mock_resp

        out = fetch_messenger_user_profile(psid="3", access_token="tok", graph_version="v23.0")

        assert out == {"name": "", "profile_pic": ""}

    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_fills_profile_pic_via_psid_picture_path_when_field_absent(self, mock_proxy: MagicMock) -> None:
        def side_effect(url: str, *args: object, **kwargs: object) -> MagicMock:
            r = MagicMock()
            r.status_code = 200
            if "/picture" in url:
                r.json.return_value = {
                    "data": {"url": "https://fbcdn.example/from-picture-edge", "is_silhouette": False},
                }
            else:
                r.json.return_value = {"name": "Nam Le", "id": "1"}
            return r

        mock_proxy.get.side_effect = side_effect

        out = fetch_messenger_user_profile(psid="66", access_token="tok", graph_version="v23.0")

        assert out["name"] == "Nam Le"
        assert out["profile_pic"] == "https://fbcdn.example/from-picture-edge"
        assert mock_proxy.get.call_count == 2


class TestFetchPageProfile:
    @patch("services.omnichannel.messenger_graph_profile.ssrf_proxy")
    def test_returns_name_and_picture(self, mock_proxy: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "My Page", "picture": {"data": {"url": "https://page.png"}}}
        mock_proxy.get.return_value = mock_resp

        out = fetch_page_profile(page_id="p1", access_token="tok", graph_version="v23.0")

        assert out == {"name": "My Page", "picture_url": "https://page.png"}
