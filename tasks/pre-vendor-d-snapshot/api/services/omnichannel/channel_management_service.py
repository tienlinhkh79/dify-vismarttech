"""Create and manage tenant-scoped channel configurations."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, NotRequired, TypedDict

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from configs import dify_config
from core.helper import encrypter
from extensions.ext_database import db
from libs.datetime_utils import naive_utc_now
from models.trigger import OmniChannelConfig, OmniChannelType
from services.feature_service import FeatureService

ZALO_PERSONAL_DRAFT_APP_PLACEHOLDER = "00000000-0000-0000-0000-000000000001"
ZALO_OA_DRAFT_APP_PLACEHOLDER = "00000000-0000-0000-0000-000000000002"
INSTAGRAM_DRAFT_APP_PLACEHOLDER = "00000000-0000-0000-0000-000000000003"
TIKTOK_DRAFT_APP_PLACEHOLDER = "00000000-0000-0000-0000-000000000004"

ALLOWED_CHANNEL_SECRET_FIELDS = frozenset({"verify_token", "client_secret", "access_token"})


def _validate_uuid_field(field_label: str, value: str) -> str:
    """Reject invalid UUIDs before DB insert (avoids opaque SQLAlchemy/DB errors)."""
    s = (value or "").strip()
    if not s:
        raise ValueError(f"{field_label} is required")
    try:
        return str(uuid.UUID(s))
    except ValueError as e:
        raise ValueError(f"{field_label} must be a valid UUID") from e


def _oauth_status_from_access_token(config: OmniChannelConfig) -> str:
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
    zalo_auto_reply_enabled: NotRequired[bool]
    zalo_info_card_enabled: NotRequired[bool]
    zalo_info_card_title: NotRequired[str | None]
    zalo_info_card_subtitle: NotRequired[str | None]
    zalo_info_card_image_url: NotRequired[str | None]
    auto_reply_pause_when_assigned: NotRequired[bool]
    auto_reply_pause_when_resolved: NotRequired[bool]
    auto_reply_business_hours_enabled: NotRequired[bool]
    auto_reply_business_hours_start: NotRequired[str | None]
    auto_reply_business_hours_end: NotRequired[str | None]
    auto_reply_timezone: NotRequired[str | None]


class ChannelManagementService:
    """Service for CRUD operations on channel records."""

    _SUPPORTED_TYPES = {
        OmniChannelType.FACEBOOK_MESSENGER.value,
        OmniChannelType.INSTAGRAM_DM.value,
        OmniChannelType.TIKTOK_MESSAGING.value,
        OmniChannelType.ZALO_OA.value,
        OmniChannelType.ZALO_PERSONAL.value,
        OmniChannelType.WEBSITE_WIDGET.value,
    }

    _PLATFORM_TO_TYPE = {
        "messenger": OmniChannelType.FACEBOOK_MESSENGER,
        "instagram": OmniChannelType.INSTAGRAM_DM,
        "tiktok": OmniChannelType.TIKTOK_MESSAGING,
        "zalo": OmniChannelType.ZALO_OA,
        "zalo_personal": OmniChannelType.ZALO_PERSONAL,
        "website": OmniChannelType.WEBSITE_WIDGET,
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
    def _resolve_branding_picture(cls, config: OmniChannelConfig) -> str | None:
        """Best-effort Page / OA avatar URL for inbox UI (requires stored access tokens)."""
        from services.omnichannel.messenger_graph_profile import fetch_page_profile
        from services.omnichannel.zalo_oa_profile import fetch_zalo_oa_display
        from services.omnichannel.zalo_oauth_service import ZaloOAuthService

        try:
            if config.channel_type in (
                OmniChannelType.FACEBOOK_MESSENGER,
                OmniChannelType.INSTAGRAM_DM,
                OmniChannelType.TIKTOK_MESSAGING,
            ):
                token = (config.decrypt_page_access_token() or "").strip()
                if not token:
                    return None
                prof = fetch_page_profile(
                    page_id=config.page_id,
                    access_token=token,
                    graph_version=config.graph_api_version,
                )
                pic = str(prof.get("picture_url") or "").strip()
                from services.omnichannel.meta_cdn import sanitize_browser_image_url

                return sanitize_browser_image_url(pic)
            if config.channel_type == OmniChannelType.ZALO_OA:
                ZaloOAuthService.refresh_tokens_for_channel(config.channel_id, leeway_seconds=3600)
                token = (config.decrypt_page_access_token() or "").strip()
                if not token:
                    return None
                disp = fetch_zalo_oa_display(access_token=token)
                pic = str(disp.get("avatar_url") or "").strip()
                return pic or None
        except Exception:
            return None
        return None

    @classmethod
    def _to_masked_dict(cls, config: OmniChannelConfig, *, include_branding: bool = False) -> dict[str, Any]:
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
            "mini_crm_business_line": config.mini_crm_business_line,
            "external_resource_picture_url": cls._resolve_branding_picture(config) if include_branding else None,
        }
        if config.channel_type in (
            OmniChannelType.ZALO_OA,
            OmniChannelType.ZALO_PERSONAL,
            OmniChannelType.FACEBOOK_MESSENGER,
            OmniChannelType.INSTAGRAM_DM,
        ):
            row["zalo_auto_reply_enabled"] = bool(config.zalo_auto_reply_enabled)
            row["auto_reply_pause_when_assigned"] = bool(config.auto_reply_pause_when_assigned)
            row["auto_reply_pause_when_resolved"] = bool(config.auto_reply_pause_when_resolved)
            row["auto_reply_business_hours_enabled"] = bool(config.auto_reply_business_hours_enabled)
            row["auto_reply_business_hours_start"] = config.auto_reply_business_hours_start
            row["auto_reply_business_hours_end"] = config.auto_reply_business_hours_end
            row["auto_reply_timezone"] = config.auto_reply_timezone
        if config.channel_type in (
            OmniChannelType.ZALO_OA,
            OmniChannelType.FACEBOOK_MESSENGER,
            OmniChannelType.INSTAGRAM_DM,
            OmniChannelType.TIKTOK_MESSAGING,
        ):
            row["oauth_status"] = _oauth_status_from_access_token(config)
        if config.channel_type == OmniChannelType.ZALO_OA:
            row["oauth_application_id"] = config.oauth_application_id
            row["oauth_callback_url"] = ZaloOAuthService.public_callback_url()
            row["zalo_info_card_enabled"] = bool(config.zalo_info_card_enabled)
            row["zalo_info_card_title"] = config.zalo_info_card_title
            row["zalo_info_card_subtitle"] = config.zalo_info_card_subtitle
            row["zalo_info_card_image_url"] = config.zalo_info_card_image_url
        if config.channel_type == OmniChannelType.ZALO_PERSONAL:
            try:
                from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService

                row["personal_login_status"] = ZaloPersonalSessionService.get_login_status(config.channel_id).get(
                    "status", "unknown"
                )
            except Exception:
                row["personal_login_status"] = "unknown"
        if config.channel_type == OmniChannelType.WEBSITE_WIDGET:
            row["embed_token"] = config.page_id
            row["embed_path"] = f"/chatbot/{config.page_id}"
            row["webhook_path"] = None
        return row

    @classmethod
    def list_channels(
        cls, tenant_id: str, channel_type: str | None = None, *, include_branding: bool = False
    ) -> list[dict[str, Any]]:
        channel_type_enum = cls._to_channel_type(channel_type) if channel_type else None
        with Session(db.engine, expire_on_commit=False) as session:
            query = session.query(OmniChannelConfig).where(OmniChannelConfig.tenant_id == tenant_id)
            if channel_type_enum:
                query = query.where(OmniChannelConfig.channel_type == channel_type_enum)
            rows = query.order_by(OmniChannelConfig.created_at.desc()).all()
        return [cls._to_masked_dict(row, include_branding=include_branding) for row in rows]

    @classmethod
    def get_channel(cls, tenant_id: str, channel_id: str, *, include_branding: bool = False) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
        if not row:
            return None
        return cls._to_masked_dict(row, include_branding=include_branding)

    @classmethod
    def get_channel_secrets(cls, tenant_id: str, channel_id: str, fields: list[str]) -> dict[str, str]:
        """Return decrypted channel secrets for workspace admins (console reveal/copy)."""
        if not fields:
            raise ValueError("At least one secret field is required")
        invalid = [field for field in fields if field not in ALLOWED_CHANNEL_SECRET_FIELDS]
        if invalid:
            raise ValueError(f"Unsupported secret fields: {', '.join(sorted(invalid))}")

        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
        if not row:
            raise ValueError("Channel not found")

        decryptors: dict[str, Callable[[], str]] = {
            "verify_token": row.decrypt_verify_token,
            "client_secret": row.decrypt_app_secret,
            "access_token": row.decrypt_page_access_token,
        }
        return {field: (decryptors[field]() or "").strip() for field in fields}

    @staticmethod
    def provision_zalo_personal_draft(tenant_id: str, user_id: str) -> dict[str, Any]:
        """Create a disabled draft channel so QR login can start before routing is configured."""
        channel_id = f"zalo-personal-{uuid.uuid4().hex[:12]}"
        suffix = channel_id[-12:]
        return ChannelManagementService.create_channel(
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "channel_type": OmniChannelType.ZALO_PERSONAL.value,
                "channel_id": channel_id,
                "app_id": ZALO_PERSONAL_DRAFT_APP_PLACEHOLDER,
                "name": "Zalo Personal",
                "external_resource_id": "personal",
                "verify_token": f"zp_vk_{suffix}",
                "client_secret": f"zp_sec_{suffix}",
                "access_token": "",
                "api_version": "v23.0",
                "enabled": False,
            },
        )

    @staticmethod
    def provision_website_widget_channel(tenant_id: str, user_id: str, app_id: str) -> dict[str, Any]:
        """Link a published web app embed to omnichannel inbox (one channel per app)."""
        from models.model import App, Site

        app_uuid = _validate_uuid_field("app_id", app_id)
        site_code = ""
        display_name = "Website Live Chat"
        with Session(db.engine, expire_on_commit=False) as session:
            app = session.scalar(select(App).where(App.id == app_uuid, App.tenant_id == tenant_id))
            if not app:
                raise ValueError("App not found")
            if not app.enable_site:
                raise ValueError("Enable Web App for this app before connecting Website Live Chat")
            site = session.scalar(select(Site).where(Site.app_id == app_uuid))
            if not site or not (site.code or "").strip():
                raise ValueError("App web site token is missing; publish the web app first")
            site_code = site.code.strip()
            display_name = (app.name or "Website").strip() or "Website Live Chat"
            existing = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.app_id == app_uuid,
                    OmniChannelConfig.channel_type == OmniChannelType.WEBSITE_WIDGET,
                )
            )
        if existing:
            return ChannelManagementService._to_masked_dict(existing)

        channel_id = f"website-{uuid.uuid4().hex[:12]}"
        suffix = channel_id[-12:]
        return ChannelManagementService.create_channel(
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "channel_type": OmniChannelType.WEBSITE_WIDGET.value,
                "channel_id": channel_id,
                "app_id": app_uuid,
                "name": display_name,
                "external_resource_id": site_code,
                "verify_token": f"ww_vk_{suffix}",
                "client_secret": f"ww_sec_{suffix}",
                "access_token": "",
                "api_version": "v23.0",
                "enabled": True,
                "zalo_auto_reply_enabled": False,
            },
        )

    @staticmethod
    def provision_zalo_oa_draft(
        tenant_id: str,
        user_id: str,
        *,
        oauth_application_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Create a disabled Zalo OA draft so OAuth can run before routing is configured."""
        app_id = (oauth_application_id or "").strip()
        secret = (client_secret or "").strip()
        if not app_id:
            raise ValueError("Zalo app ID is required")
        if not secret:
            raise ValueError("OA secret key is required")
        channel_id = f"zalo-oa-{uuid.uuid4().hex[:12]}"
        suffix = channel_id[-12:]
        return ChannelManagementService.create_channel(
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "channel_type": OmniChannelType.ZALO_OA.value,
                "channel_id": channel_id,
                "app_id": ZALO_OA_DRAFT_APP_PLACEHOLDER,
                "name": "Zalo OA",
                "external_resource_id": "pending",
                "oauth_application_id": app_id,
                "verify_token": f"zo_vk_{suffix}",
                "client_secret": secret,
                "access_token": "",
                "api_version": "v23.0",
                "enabled": False,
            },
        )

    @staticmethod
    def provision_oauth_channel_draft(tenant_id: str, user_id: str, *, channel_type: str) -> dict[str, Any]:
        """Create a disabled draft channel so credentials can be configured before routing."""
        normalized = ChannelManagementService._to_channel_type(channel_type)
        if normalized == OmniChannelType.INSTAGRAM_DM:
            prefix = "instagram"
            placeholder = INSTAGRAM_DRAFT_APP_PLACEHOLDER
            default_name = "Instagram DM"
        elif normalized == OmniChannelType.TIKTOK_MESSAGING:
            prefix = "tiktok"
            placeholder = TIKTOK_DRAFT_APP_PLACEHOLDER
            default_name = "TikTok Messaging"
        else:
            raise ValueError("Unsupported channel type for OAuth draft provisioning")
        channel_id = f"{prefix}-{uuid.uuid4().hex[:12]}"
        suffix = channel_id[-12:]
        return ChannelManagementService.create_channel(
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "channel_type": normalized.value,
                "channel_id": channel_id,
                "app_id": placeholder,
                "name": default_name,
                "external_resource_id": "pending",
                "verify_token": f"{prefix[:2]}_vk_{suffix}",
                "client_secret": f"{prefix[:2]}_sec_{suffix}",
                "access_token": "",
                "api_version": "v23.0",
                "enabled": False,
            },
        )

    @staticmethod
    def create_channel(tenant_id: str, user_id: str, payload: ChannelInput) -> dict[str, Any]:
        channel_type = ChannelManagementService._to_channel_type(payload["channel_type"])
        access_token_plain = (payload.get("access_token") or "").strip()
        oauth_application_id = (payload.get("oauth_application_id") or "").strip() or None

        if channel_type == OmniChannelType.ZALO_OA and not access_token_plain and not oauth_application_id:
            raise ValueError("Zalo OA requires oauth_application_id when access_token is empty")
        if channel_type == OmniChannelType.ZALO_PERSONAL or channel_type == OmniChannelType.WEBSITE_WIDGET:
            access_token_plain = ""
        elif channel_type != OmniChannelType.ZALO_OA and not access_token_plain:
            is_disabled_draft = not payload.get("enabled", True)
            allows_empty_token = channel_type in (
                OmniChannelType.INSTAGRAM_DM,
                OmniChannelType.TIKTOK_MESSAGING,
            )
            if not (is_disabled_draft and allows_empty_token):
                raise ValueError("access_token is required for this channel type")

        verify_token_plain = (payload.get("verify_token") or "").strip()
        client_secret_plain = (payload.get("client_secret") or "").strip()
        external_resource_id = (payload.get("external_resource_id") or "").strip()
        if channel_type == OmniChannelType.ZALO_PERSONAL:
            if not external_resource_id:
                external_resource_id = "personal"
            if not verify_token_plain:
                verify_token_plain = f"zp_vk_{payload['channel_id'][:12]}"
            if not client_secret_plain:
                client_secret_plain = f"zp_sec_{payload['channel_id'][:12]}"
        if channel_type == OmniChannelType.WEBSITE_WIDGET:
            if not external_resource_id:
                raise ValueError("external_resource_id (embed token) is required for website widget")
            if not verify_token_plain:
                verify_token_plain = f"ww_vk_{payload['channel_id'][:12]}"
            if not client_secret_plain:
                client_secret_plain = f"ww_sec_{payload['channel_id'][:12]}"

        tenant_uuid = _validate_uuid_field("tenant_id", tenant_id)
        user_uuid = _validate_uuid_field("user_id", user_id)
        app_uuid = _validate_uuid_field("app_id", payload["app_id"])

        encrypted_access: str | None
        if access_token_plain:
            encrypted_access = encrypter.encrypt_token(tenant_uuid, access_token_plain)
        else:
            encrypted_access = None

        with Session(db.engine, expire_on_commit=False) as session:
            existed = session.scalar(
                select(OmniChannelConfig).where(OmniChannelConfig.channel_id == payload["channel_id"])
            )
            if existed:
                raise ValueError("Channel ID already exists")

            if dify_config.BILLING_ENABLED:
                feats = FeatureService.get_features(tenant_id)
                oc = feats.omnichannel_channels
                limit_n = int(getattr(oc, "limit", 0) or 0)
                size_n = int(getattr(oc, "size", 0) or 0)
                if 0 < limit_n <= size_n:
                    raise ValueError("The number of omnichannel channels has reached the limit of your subscription.")

            auto_reply_default = channel_type in (
                OmniChannelType.ZALO_PERSONAL,
                OmniChannelType.FACEBOOK_MESSENGER,
                OmniChannelType.INSTAGRAM_DM,
            )
            zalo_auto_reply = bool(payload.get("zalo_auto_reply_enabled", auto_reply_default))
            zalo_info_card = bool(payload.get("zalo_info_card_enabled", False))
            supports_auto_reply_policy = channel_type in (
                OmniChannelType.ZALO_OA,
                OmniChannelType.ZALO_PERSONAL,
                OmniChannelType.FACEBOOK_MESSENGER,
                OmniChannelType.INSTAGRAM_DM,
            )
            row = OmniChannelConfig(
                tenant_id=tenant_uuid,
                app_id=app_uuid,
                user_id=user_uuid,
                name=payload["name"],
                channel_type=channel_type,
                channel_id=payload["channel_id"],
                enabled=payload["enabled"],
                zalo_auto_reply_enabled=zalo_auto_reply if supports_auto_reply_policy else False,
                auto_reply_pause_when_assigned=bool(payload.get("auto_reply_pause_when_assigned", True))
                if supports_auto_reply_policy
                else True,
                auto_reply_pause_when_resolved=bool(payload.get("auto_reply_pause_when_resolved", True))
                if supports_auto_reply_policy
                else True,
                auto_reply_business_hours_enabled=bool(payload.get("auto_reply_business_hours_enabled", False))
                if supports_auto_reply_policy
                else False,
                auto_reply_business_hours_start=(
                    (payload.get("auto_reply_business_hours_start") or None)
                    if supports_auto_reply_policy
                    else None
                ),
                auto_reply_business_hours_end=(
                    (payload.get("auto_reply_business_hours_end") or None)
                    if supports_auto_reply_policy
                    else None
                ),
                auto_reply_timezone=(
                    (payload.get("auto_reply_timezone") or "Asia/Ho_Chi_Minh").strip() or "Asia/Ho_Chi_Minh"
                )
                if supports_auto_reply_policy
                else "Asia/Ho_Chi_Minh",
                zalo_info_card_enabled=zalo_info_card if channel_type == OmniChannelType.ZALO_OA else False,
                zalo_info_card_title=(payload.get("zalo_info_card_title") or None)
                if channel_type == OmniChannelType.ZALO_OA
                else None,
                zalo_info_card_subtitle=(payload.get("zalo_info_card_subtitle") or None)
                if channel_type == OmniChannelType.ZALO_OA
                else None,
                zalo_info_card_image_url=(payload.get("zalo_info_card_image_url") or None)
                if channel_type == OmniChannelType.ZALO_OA
                else None,
                page_id=external_resource_id,
                graph_api_version=payload["api_version"],
                oauth_application_id=oauth_application_id if channel_type == OmniChannelType.ZALO_OA else None,
                encrypted_verify_token=encrypter.encrypt_token(tenant_uuid, verify_token_plain),
                encrypted_app_secret=encrypter.encrypt_token(tenant_uuid, client_secret_plain),
                encrypted_page_access_token=encrypted_access,
                encrypted_oa_refresh_token=None,
                oa_token_expires_at=None,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as e:
                session.rollback()
                raise ValueError(
                    "Channel ID already exists or conflicts with existing data."
                ) from e
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
                row.app_id = _validate_uuid_field("app_id", str(payload["app_id"]))
            if "external_resource_id" in payload:
                row.page_id = payload["external_resource_id"]
            if "api_version" in payload:
                row.graph_api_version = payload["api_version"]
            if "enabled" in payload:
                row.enabled = payload["enabled"]
            if "mini_crm_business_line" in payload:
                from models.trigger import MiniCrmBusinessLine

                raw_line = payload.get("mini_crm_business_line")
                if raw_line is None or str(raw_line).strip() == "":
                    row.mini_crm_business_line = None
                else:
                    normalized = MiniCrmBusinessLine.normalize(str(raw_line))
                    if not normalized:
                        raise ValueError("Invalid mini_crm_business_line")
                    row.mini_crm_business_line = normalized
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
            if "zalo_auto_reply_enabled" in payload and row.channel_type in (
                OmniChannelType.ZALO_OA,
                OmniChannelType.ZALO_PERSONAL,
                OmniChannelType.FACEBOOK_MESSENGER,
                OmniChannelType.INSTAGRAM_DM,
            ):
                row.zalo_auto_reply_enabled = bool(payload["zalo_auto_reply_enabled"])
            if row.channel_type in (
                OmniChannelType.ZALO_OA,
                OmniChannelType.ZALO_PERSONAL,
                OmniChannelType.FACEBOOK_MESSENGER,
                OmniChannelType.INSTAGRAM_DM,
            ):
                if "auto_reply_pause_when_assigned" in payload:
                    row.auto_reply_pause_when_assigned = bool(payload["auto_reply_pause_when_assigned"])
                if "auto_reply_pause_when_resolved" in payload:
                    row.auto_reply_pause_when_resolved = bool(payload["auto_reply_pause_when_resolved"])
                if "auto_reply_business_hours_enabled" in payload:
                    row.auto_reply_business_hours_enabled = bool(payload["auto_reply_business_hours_enabled"])
                if "auto_reply_business_hours_start" in payload:
                    row.auto_reply_business_hours_start = payload.get("auto_reply_business_hours_start") or None
                if "auto_reply_business_hours_end" in payload:
                    row.auto_reply_business_hours_end = payload.get("auto_reply_business_hours_end") or None
                if "auto_reply_timezone" in payload:
                    tz = str(payload.get("auto_reply_timezone") or "").strip()
                    row.auto_reply_timezone = tz or "Asia/Ho_Chi_Minh"
            if row.channel_type == OmniChannelType.ZALO_OA:
                if "zalo_info_card_enabled" in payload:
                    row.zalo_info_card_enabled = bool(payload["zalo_info_card_enabled"])
                if "zalo_info_card_title" in payload:
                    row.zalo_info_card_title = (payload.get("zalo_info_card_title") or None)
                if "zalo_info_card_subtitle" in payload:
                    row.zalo_info_card_subtitle = (payload.get("zalo_info_card_subtitle") or None)
                if "zalo_info_card_image_url" in payload:
                    row.zalo_info_card_image_url = (payload.get("zalo_info_card_image_url") or None)

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

