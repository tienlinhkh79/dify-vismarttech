"""Read tenant-scoped omnichannel channel configurations."""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.trigger import OmniChannelConfig, OmniChannelType


class MessengerChannelConfig(TypedDict):
    tenant_id: str
    app_id: str
    channel_id: str
    page_id: str
    verify_token: str
    app_secret: str
    page_access_token: str
    graph_api_version: str


class ChannelConfigService:
    """Load omnichannel credentials by external channel identifier."""

    @staticmethod
    def get_messenger_channel_config(channel_id: str) -> MessengerChannelConfig | None:
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type == OmniChannelType.FACEBOOK_MESSENGER,
                    OmniChannelConfig.enabled.is_(True),
                )
            )
        if not config:
            return None

        return {
            "tenant_id": config.tenant_id,
            "app_id": config.app_id,
            "channel_id": config.channel_id,
            "page_id": config.page_id,
            "verify_token": config.decrypt_verify_token(),
            "app_secret": config.decrypt_app_secret(),
            "page_access_token": config.decrypt_page_access_token(),
            "graph_api_version": config.graph_api_version,
        }

