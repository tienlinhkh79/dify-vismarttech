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
            "display_name": "Facebook Page",
            "status": "active",
            "setup_kind": "oauth_or_token",
        },
        {
            "provider": "instagram",
            "channel_type": "instagram_dm",
            "display_name": "Instagram Messaging",
            "status": "active",
            "setup_kind": "oauth_meta",
        },
        {
            "provider": "tiktok",
            "channel_type": "tiktok_messaging",
            "display_name": "TikTok Business Messaging",
            "status": "active",
            "setup_kind": "oauth_or_token",
        },
        {
            "provider": "zalo",
            "channel_type": "zalo_oa",
            "display_name": "Zalo Official Account (OA)",
            "status": "active",
            "setup_kind": "oauth_zalo",
        },
        {
            "provider": "zalo_personal",
            "channel_type": "zalo_personal",
            "display_name": "Zalo Personal",
            "status": "active",
            "setup_kind": "qr_zalo_personal",
        },
        {
            "provider": "website",
            "channel_type": "website_widget",
            "display_name": "Website Live Chat",
            "status": "coming_soon",
            "setup_kind": "embed_script",
        },
        {
            "provider": "whatsapp",
            "channel_type": "whatsapp_cloud",
            "display_name": "WhatsApp Business",
            "status": "coming_soon",
            "setup_kind": "embedded_signup",
        },
        {
            "provider": "email",
            "channel_type": "email_imap",
            "display_name": "Email",
            "status": "coming_soon",
            "setup_kind": "oauth_email",
        },
        {
            "provider": "telegram",
            "channel_type": "telegram_bot",
            "display_name": "Telegram",
            "status": "coming_soon",
            "setup_kind": "bot_token",
        },
    ]

    @classmethod
    def list(cls) -> list[ProviderMetadata]:
        return cls._PROVIDERS.copy()

