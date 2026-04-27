"""Registry for available channel provider adapters."""

from __future__ import annotations

from typing import TypedDict


class ProviderMetadata(TypedDict):
    provider: str
    channel_type: str
    display_name: str
    status: str
    setup_kind: str


class ChannelProviderRegistry:
    """Static registry for current supported providers."""

    _PROVIDERS: list[ProviderMetadata] = [
        {
            "provider": "messenger",
            "channel_type": "facebook_messenger",
            "display_name": "Messenger (Facebook Page)",
            "status": "active",
            "setup_kind": "oauth_or_token",
        },
        {
            "provider": "instagram",
            "channel_type": "instagram_dm",
            "display_name": "Instagram Direct Message",
            "status": "coming_soon",
            "setup_kind": "oauth_meta",
        },
        {
            "provider": "tiktok",
            "channel_type": "tiktok_messaging",
            "display_name": "TikTok Messaging",
            "status": "coming_soon",
            "setup_kind": "oauth_tiktok",
        },
    ]

    @classmethod
    def list(cls) -> list[ProviderMetadata]:
        return cls._PROVIDERS.copy()

