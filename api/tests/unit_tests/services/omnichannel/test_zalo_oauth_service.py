from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.trigger import OmniChannelType
from services.omnichannel.zalo_oauth_service import ZaloOAuthService


class _Row:
    tenant_id = "tenant-1"
    channel_id = "channel-1"
    channel_type = OmniChannelType.ZALO_OA
    oauth_application_id = "zalo-app-9"


def test_pkce_challenge_has_no_padding():
    _verifier, challenge = ZaloOAuthService._pkce_pair()
    assert "=" not in challenge
    assert len(challenge) > 32


@patch("services.omnichannel.zalo_oauth_service.redis_client")
@patch("services.omnichannel.zalo_oauth_service.Session")
def test_start_stores_redis_state(mock_session_cls, mock_redis):
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None
    mock_session.scalar.return_value = _Row()
    mock_session_cls.return_value = mock_session

    out = ZaloOAuthService.start("tenant-1", "channel-1")

    assert "qr_data_uri" in out
    assert out["qr_data_uri"].startswith("data:image/png;base64,")
    assert "code_challenge=" in out["auth_url"]
    mock_redis.setex.assert_called_once()
    _key, ttl, _payload = mock_redis.setex.call_args[0]
    assert ttl == ZaloOAuthService.STATE_TTL_SECONDS


@patch("services.omnichannel.zalo_oauth_service.redis_client")
def test_handle_callback_rejects_missing_state(mock_redis):
    mock_redis.get.return_value = None
    with pytest.raises(ValueError, match="Invalid or expired"):
        ZaloOAuthService.handle_callback(code="abc", state="nope")
