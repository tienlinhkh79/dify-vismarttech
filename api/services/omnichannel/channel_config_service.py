"""Read tenant-scoped omnichannel channel configurations."""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelConfig, OmniChannelType
from services.omnichannel.zalo_oauth_service import ZaloOAuthService


class MessengerChannelConfig(TypedDict):
    tenant_id: str
    app_id: str
    channel_id: str
    channel_type: str
    page_id: str
    verify_token: str
    app_secret: str
    page_access_token: str
    graph_api_version: str


class ZaloChannelConfig(TypedDict):
    tenant_id: str
    app_id: str
    channel_id: str
    oa_id: str
    verify_token: str
    app_secret: str
    oa_access_token: str


class ChannelConfigService:
    """Load omnichannel credentials by external channel identifier."""

    @staticmethod
    def get_meta_channel_config(channel_id: str) -> MessengerChannelConfig | None:
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type.in_(
                        [
                            OmniChannelType.FACEBOOK_MESSENGER,
                            OmniChannelType.INSTAGRAM_DM,
                            OmniChannelType.TIKTOK_MESSAGING,
                        ]
                    ),
                    OmniChannelConfig.enabled.is_(True),
                )
            )
        if not config:
            return None

        return {
            "tenant_id": config.tenant_id,
            "app_id": config.app_id,
            "channel_id": config.channel_id,
            "channel_type": config.channel_type.value,
            "page_id": config.page_id,
            "verify_token": config.decrypt_verify_token(),
            "app_secret": config.decrypt_app_secret(),
            "page_access_token": config.decrypt_page_access_token(),
            "graph_api_version": config.graph_api_version,
        }

    @staticmethod
    def get_messenger_channel_config(channel_id: str) -> MessengerChannelConfig | None:
        # Backward compatible alias used by existing routes.
        return ChannelConfigService.get_meta_channel_config(channel_id)

    @staticmethod
    def get_zalo_channel_config(channel_id: str) -> ZaloChannelConfig | None:
        ZaloOAuthService.refresh_tokens_for_channel(channel_id, leeway_seconds=3600)
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                    OmniChannelConfig.enabled.is_(True),
                )
            )
        if not config:
            return None

        access_token = config.decrypt_page_access_token().strip()
        if not access_token:
            return None

        return {
            "tenant_id": config.tenant_id,
            "app_id": config.app_id,
            "channel_id": config.channel_id,
            "oa_id": config.page_id,
            "verify_token": config.decrypt_verify_token(),
            "app_secret": config.decrypt_app_secret(),
            "oa_access_token": access_token,
        }

