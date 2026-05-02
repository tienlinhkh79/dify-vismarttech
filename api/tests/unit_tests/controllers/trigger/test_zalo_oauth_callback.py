from __future__ import annotations

from unittest.mock import patch

import controllers.trigger.zalo as module


class MockRequest:
    def __init__(self, args=None):
        self.args = args or {}


@patch.object(module.dify_config, "CONSOLE_WEB_URL", "https://console.example.com")
@patch.object(module, "redirect", side_effect=lambda url: url)
def test_oauth_callback_redirects_on_error(_mock_redirect):
    module.request = MockRequest(args={"error": "access_denied", "error_description": "nope"})
    url = module.zalo_oauth_callback()
    assert "zalo_oauth=error" in url
    assert "reason=" in url


@patch.object(module.dify_config, "CONSOLE_WEB_URL", "https://console.example.com")
@patch.object(module.ZaloOAuthService, "handle_callback", return_value="channel-zalo-1")
@patch.object(module, "redirect", side_effect=lambda url: url)
def test_oauth_callback_redirects_on_success(_mock_cb):
    module.request = MockRequest(args={"code": "c1", "state": "s1"})
    url = module.zalo_oauth_callback()
    assert "zalo_oauth=success" in url
    assert "channel-zalo-1" in url


@patch.object(module.dify_config, "CONSOLE_WEB_URL", "https://console.example.com")
@patch.object(module.ZaloOAuthService, "handle_callback", side_effect=ValueError("bad"))
@patch.object(module, "redirect", side_effect=lambda url: url)
def test_oauth_callback_redirects_on_value_error(_mock_cb):
    module.request = MockRequest(args={"code": "c1", "state": "s1"})
    url = module.zalo_oauth_callback()
    assert "zalo_oauth=error" in url
