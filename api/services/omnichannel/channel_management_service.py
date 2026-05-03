"""Create and manage tenant-scoped channel configurations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NotRequired, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from configs import dify_config
from core.helper import encrypter
from extensions.ext_database import db
from libs.datetime_utils import naive_utc_now
from models.trigger import OmniChannelConfig, OmniChannelType
from services.feature_service import FeatureService


def _zalo_oauth_status(config: OmniChannelConfig) -> str:
    has_access = bool(
        config.encrypted_page_access_token and config.decrypt_page_access_token().strip()
    )
    if not has_access:
        return "pending_auth"
    if (
        config.oa_token_expires_at
        and config.oa_token_expires_at < naive_utc_now()
        and not config.encrypted_oa_refresh_token
    ):
        return "expired"
    return "connected"


class ChannelInput(TypedDict):
    channel_type: str
    channel_id: str
    app_id: str
    name: str
    external_resource_id: str
    verify_token: str
    access_token: str
    client_secret: str
    api_version: str
    enabled: bool
    oauth_application_id: NotRequired[str | None]


class ChannelManagementService:
    """Service for CRUD operations on channel records."""

    _SUPPORTED_TYPES = {
        OmniChannelType.FACEBOOK_MESSENGER.value,
        OmniChannelType.INSTAGRAM_DM.value,
        OmniChannelType.TIKTOK_MESSAGING.value,
        OmniChannelType.ZALO_OA.value,
    }

    _PLATFORM_TO_TYPE = {
        "messenger": OmniChannelType.FACEBOOK_MESSENGER,
        "instagram": OmniChannelType.INSTAGRAM_DM,
        "tiktok": OmniChannelType.TIKTOK_MESSAGING,
        "zalo": OmniChannelType.ZALO_OA,
    }

    _TYPE_TO_PLATFORM = {value: key for key, value in _PLATFORM_TO_TYPE.items()}

    @classmethod
    def _to_channel_type(cls, channel_type: str) -> OmniChannelType:
        try:
            enum_type = OmniChannelType(channel_type)
        except ValueError as e:
            raise ValueError(f"Unsupported channel_type: {channel_type}") from e
        if enum_type.value not in cls._SUPPORTED_TYPES:
            raise ValueError(f"Unsupported channel_type: {channel_type}")
        return enum_type

    @classmethod
    def _secret_fingerprint(cls, get_plain: Callable[[], str]) -> str:
        """Non-reversible hint so the console can show that a secret is stored (last chars only)."""
        try:
            plain = (get_plain() or "").strip()
        except Exception:
            return ""
        return encrypter.obfuscated_token(plain) if plain else ""

    @classmethod
    def _to_masked_dict(cls, config: OmniChannelConfig) -> dict[str, Any]:
        from services.omnichannel.zalo_oauth_service import ZaloOAuthService

        platform = cls._TYPE_TO_PLATFORM.get(config.channel_type, "messenger")
        callback_path = f"/triggers/{platform}/webhook/{config.channel_id}"
        row: dict[str, Any] = {
            "id": config.id,
            "channel_id": config.channel_id,
            "channel_type": config.channel_type.value,
            "platform": platform,
            "name": config.name,
            "app_id": config.app_id,
            "external_resource_id": config.page_id,
            "api_version": config.graph_api_version,
            "enabled": config.enabled,
            "status": "active" if config.enabled else "inactive",
            "webhook_path": callback_path,
            "verify_token_masked": cls._secret_fingerprint(config.decrypt_verify_token),
            "client_secret_masked": cls._secret_fingerprint(config.decrypt_app_secret),
            "access_token_masked": cls._secret_fingerprint(config.decrypt_page_access_token),
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        if config.channel_type == OmniChannelType.ZALO_OA:
            row["oauth_status"] = _zalo_oauth_status(config)
            row["oauth_application_id"] = config.oauth_application_id
            row["oauth_callback_url"] = ZaloOAuthService.public_callback_url()
        return row

    @classmethod
    def list_channels(cls, tenant_id: str, channel_type: str | None = None) -> list[dict[str, Any]]:
        channel_type_enum = cls._to_channel_type(channel_type) if channel_type else None
        with Session(db.engine, expire_on_commit=False) as session:
            query = session.query(OmniChannelConfig).where(OmniChannelConfig.tenant_id == tenant_id)
            if channel_type_enum:
                query = query.where(OmniChannelConfig.channel_type == channel_type_enum)
            rows = query.order_by(OmniChannelConfig.created_at.desc()).all()
        return [cls._to_masked_dict(row) for row in rows]

    @classmethod
    def get_channel(cls, tenant_id: str, channel_id: str) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
        if not row:
            return None
        return cls._to_masked_dict(row)

    @staticmethod
    def create_channel(tenant_id: str, user_id: str, payload: ChannelInput) -> dict[str, Any]:
        channel_type = ChannelManagementService._to_channel_type(payload["channel_type"])
        access_token_plain = (payload.get("access_token") or "").strip()
        oauth_application_id = (payload.get("oauth_application_id") or "").strip() or None

        if channel_type != OmniChannelType.ZALO_OA and not access_token_plain:
            raise ValueError("access_token is required for this channel type")

        if channel_type == OmniChannelType.ZALO_OA and not access_token_plain and not oauth_application_id:
            raise ValueError("Zalo OA requires oauth_application_id when access_token is empty")

        encrypted_access: str | None
        if access_token_plain:
            encrypted_access = encrypter.encrypt_token(tenant_id, access_token_plain)
        else:
            encrypted_access = None

        with Session(db.engine, expire_on_commit=False) as session:
            existed = session.scalar(select(OmniChannelConfig).where(OmniChannelConfig.channel_id == payload["channel_id"]))
            if existed:
                raise ValueError("Channel ID already exists")

            if dify_config.BILLING_ENABLED:
                feats = FeatureService.get_features(tenant_id)
                ch = feats.omnichannel_channels
                if 0 < ch.limit <= ch.size:
                    raise ValueError("The number of omnichannel channels has reached the limit of your subscription.")

            row = OmniChannelConfig(
                tenant_id=tenant_id,
                app_id=payload["app_id"],
                user_id=user_id,
                name=payload["name"],
                channel_type=channel_type,
                channel_id=payload["channel_id"],
                enabled=payload["enabled"],
                page_id=payload["external_resource_id"],
                graph_api_version=payload["api_version"],
                oauth_application_id=oauth_application_id,
                encrypted_verify_token=encrypter.encrypt_token(tenant_id, payload["verify_token"]),
                encrypted_app_secret=encrypter.encrypt_token(tenant_id, payload["client_secret"]),
                encrypted_page_access_token=encrypted_access,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return ChannelManagementService._to_masked_dict(row)

    @staticmethod
    def update_channel(tenant_id: str, channel_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
            if not row:
                raise ValueError("Channel not found")

            if "name" in payload:
                row.name = payload["name"]
            if "app_id" in payload:
                row.app_id = payload["app_id"]
            if "external_resource_id" in payload:
                row.page_id = payload["external_resource_id"]
            if "api_version" in payload:
                row.graph_api_version = payload["api_version"]
            if "enabled" in payload:
                row.enabled = payload["enabled"]
            if "verify_token" in payload:
                row.encrypted_verify_token = encrypter.encrypt_token(tenant_id, payload["verify_token"])
            if "client_secret" in payload:
                row.encrypted_app_secret = encrypter.encrypt_token(tenant_id, payload["client_secret"])
            if "oauth_application_id" in payload:
                zid = payload["oauth_application_id"]
                row.oauth_application_id = (str(zid).strip() if zid else "") or None
            if "access_token" in payload:
                at = payload["access_token"]
                if row.channel_type == OmniChannelType.ZALO_OA:
                    if at and str(at).strip():
                        row.encrypted_page_access_token = encrypter.encrypt_token(tenant_id, str(at).strip())
                elif at:
                    row.encrypted_page_access_token = encrypter.encrypt_token(tenant_id, str(at))
            if "channel_type" in payload:
                row.channel_type = ChannelManagementService._to_channel_type(payload["channel_type"])

            session.commit()
            session.refresh(row)
            return ChannelManagementService._to_masked_dict(row)

    @staticmethod
    def delete_channel(tenant_id: str, channel_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
            if not row:
                raise ValueError("Channel not found")
            session.delete(row)
            session.commit()

    @classmethod
    def list_messenger_channels(cls, tenant_id: str) -> list[dict[str, Any]]:
        return cls.list_channels(tenant_id=tenant_id, channel_type=OmniChannelType.FACEBOOK_MESSENGER.value)

    @classmethod
    def get_messenger_channel(cls, tenant_id: str, channel_id: str) -> dict[str, Any] | None:
        channel = cls.get_channel(tenant_id, channel_id)
        if not channel or channel["channel_type"] != OmniChannelType.FACEBOOK_MESSENGER.value:
            return None
        return channel

    @staticmethod
    def create_messenger_channel(tenant_id: str, user_id: str, payload: ChannelInput) -> dict[str, Any]:
        payload["channel_type"] = OmniChannelType.FACEBOOK_MESSENGER.value
        return ChannelManagementService.create_channel(tenant_id, user_id, payload)

    @staticmethod
    def update_messenger_channel(tenant_id: str, channel_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return ChannelManagementService.update_channel(tenant_id, channel_id, payload)

    @staticmethod
    def delete_messenger_channel(tenant_id: str, channel_id: str) -> None:
        ChannelManagementService.delete_channel(tenant_id, channel_id)

