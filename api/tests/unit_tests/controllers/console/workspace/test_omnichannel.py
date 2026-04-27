from types import SimpleNamespace
from unittest.mock import patch

import pytest
from werkzeug.exceptions import NotFound

import controllers.console.workspace.omnichannel as module


@pytest.fixture(autouse=True)
def _mock_jsonable_encoder():
    module.jsonable_encoder = lambda payload: payload


class TestMessengerChannelCollectionApi:
    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "list_messenger_channels", return_value=[{"channel_id": "ch-1"}])
    def test_get_channels(self, _mock_list, _mock_current):
        result = module.MessengerChannelCollectionApi().get()
        assert result["data"][0]["channel_id"] == "ch-1"

    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "create_messenger_channel", return_value={"channel_id": "ch-1"})
    @patch.object(module, "console_ns")
    def test_create_channel(self, mock_ns, _mock_create, _mock_current):
        mock_ns.payload = {
            "channel_id": "ch-1",
            "app_id": "app-1",
            "name": "Page A",
            "page_id": "page-1",
            "verify_token": "vt",
            "app_secret": "secret",
            "page_access_token": "pat",
            "graph_api_version": "v23.0",
            "enabled": True,
        }
        result, status = module.MessengerChannelCollectionApi().post()
        assert status == 201
        assert result["data"]["channel_id"] == "ch-1"


class TestMessengerChannelApi:
    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "get_messenger_channel", return_value={"channel_id": "ch-1"})
    def test_get_one_channel(self, _mock_get, _mock_current):
        result = module.MessengerChannelApi().get("ch-1")
        assert result["data"]["channel_id"] == "ch-1"

    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "get_messenger_channel", return_value=None)
    def test_get_channel_not_found(self, _mock_get, _mock_current):
        with pytest.raises(NotFound):
            module.MessengerChannelApi().get("missing")

    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "update_messenger_channel", return_value={"channel_id": "ch-1"})
    @patch.object(module, "console_ns")
    def test_patch_channel(self, mock_ns, _mock_update, _mock_current):
        mock_ns.payload = {"enabled": False}
        result = module.MessengerChannelApi().patch("ch-1")
        assert result["data"]["channel_id"] == "ch-1"

    @patch.object(module, "current_account_with_tenant", return_value=(SimpleNamespace(id="user-1"), "tenant-1"))
    @patch.object(module.ChannelManagementService, "delete_messenger_channel", return_value=None)
    def test_delete_channel(self, _mock_delete, _mock_current):
        result, status = module.MessengerChannelApi().delete("ch-1")
        assert status == 200
        assert result["result"] == "success"

