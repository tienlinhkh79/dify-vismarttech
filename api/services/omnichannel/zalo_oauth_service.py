"""Zalo Official Account OAuth 2.0 (authorization code + PKCE) helpers."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import secrets
from datetime import timedelta
from typing import Any, TypedDict
from urllib.parse import urlencode
from uuid import uuid4

import segno
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from configs import dify_config
from core.helper import encrypter
from core.helper.ssrf_proxy import ssrf_proxy
from extensions.ext_database import db
from extensions.ext_redis import redis_client
from libs.datetime_utils import naive_utc_now
from models.trigger import OmniChannelConfig, OmniChannelType

logger = logging.getLogger(__name__)


class _OAuthStatePayload(TypedDict):
    tenant_id: str
    channel_id: str
    code_verifier: str


class ZaloOAuthService:
    AUTH_URL = "https://oauth.zaloapp.com/v4/oa/permission"
    TOKEN_URL = "https://oauth.zaloapp.com/v4/oa/access_token"
    REDIS_KEY_PREFIX = "zalo_oauth:state:"
    STATE_TTL_SECONDS = 600

    @classmethod
    def _redis_key(cls, state: str) -> str:
        return f"{cls.REDIS_KEY_PREFIX}{state}"

    @classmethod
    def public_callback_url(cls) -> str:
        """Public redirect_uri registered in Zalo Developer (same host as TRIGGER_URL)."""
        return f"{dify_config.TRIGGER_URL.rstrip('/')}/triggers/zalo/oauth/callback"

    @classmethod
    def _pkce_pair(cls) -> tuple[str, str]:
        code_verifier = secrets.token_urlsafe(48)
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge

    @classmethod
    def _qr_data_uri(cls, auth_url: str) -> str:
        buf = io.BytesIO()
        segno.make(auth_url).save(buf, kind="png", scale=6)
        raw = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{raw}"

    @classmethod
    def start(cls, tenant_id: str, channel_id: str) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                )
            )
        if not row:
            raise ValueError("Zalo channel not found")
        if not row.oauth_application_id:
            raise ValueError("Zalo OAuth application id is not configured for this channel")

        code_verifier, code_challenge = cls._pkce_pair()
        state = str(uuid4())
        payload: _OAuthStatePayload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "code_verifier": code_verifier,
        }
        redis_client.setex(
            cls._redis_key(state),
            cls.STATE_TTL_SECONDS,
            json.dumps(payload),
        )

        query = urlencode(
            {
                "app_id": row.oauth_application_id,
                "redirect_uri": cls.public_callback_url(),
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        auth_url = f"{cls.AUTH_URL}?{query}"

        return {
            "auth_url": auth_url,
            "qr_data_uri": cls._qr_data_uri(auth_url),
            "state": state,
            "expires_in": cls.STATE_TTL_SECONDS,
            "oauth_callback_url": cls.public_callback_url(),
        }

    @classmethod
    def _decode_state(cls, state: str | None) -> _OAuthStatePayload:
        if not state:
            raise ValueError("Missing OAuth state")
        raw = redis_client.get(cls._redis_key(state))
        if raw is None:
            raise ValueError("Invalid or expired OAuth state")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return _OAuthStatePayload(
            tenant_id=str(data["tenant_id"]),
            channel_id=str(data["channel_id"]),
            code_verifier=str(data["code_verifier"]),
        )

    @classmethod
    def _post_token(cls, *, app_secret: str, form_body: dict[str, str]) -> dict[str, Any]:
        response = ssrf_proxy.post(
            cls.TOKEN_URL,
            data=form_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "secret_key": app_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected token response shape")
        if payload.get("error"):
            raise ValueError(str(payload.get("error_description") or payload.get("error")))
        return payload

    @classmethod
    def handle_callback(cls, *, code: str | None, state: str | None) -> str:
        if not code:
            raise ValueError("Missing authorization code")
        oauth_state = cls._decode_state(state)
        redis_client.delete(cls._redis_key(state or ""))

        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == oauth_state["tenant_id"],
                    OmniChannelConfig.channel_id == oauth_state["channel_id"],
                    OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                )
            )
            if not row or not row.oauth_application_id:
                raise ValueError("Zalo channel not found")

            app_secret = row.decrypt_app_secret()
            token_payload = cls._post_token(
                app_secret=app_secret,
                form_body={
                    "code": code,
                    "app_id": row.oauth_application_id,
                    "grant_type": "authorization_code",
                    "code_verifier": oauth_state["code_verifier"],
                },
            )

            access_token = str(token_payload.get("access_token") or "")
            if not access_token:
                raise ValueError("Token response missing access_token")

            refresh_token = str(token_payload.get("refresh_token") or "")
            expires_in = int(token_payload.get("expires_in") or 90000)
            tenant_id = row.tenant_id

            row.encrypted_page_access_token = encrypter.encrypt_token(tenant_id, access_token)
            if refresh_token:
                row.encrypted_oa_refresh_token = encrypter.encrypt_token(tenant_id, refresh_token)
            row.oa_token_expires_at = naive_utc_now() + timedelta(seconds=max(expires_in - 60, 60))

            session.commit()
            channel_id = row.channel_id

        logger.info("Zalo OA OAuth completed for channel_id=%s", channel_id)
        return channel_id

    @classmethod
    def refresh_tokens_for_channel(
        cls,
        channel_id: str,
        *,
        leeway_seconds: int | None = 3600,
        force: bool = False,
    ) -> bool:
        """Refresh access token using refresh_token when near expiry. Returns True if refreshed."""
        now = naive_utc_now()
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                )
            )
            if not row or not row.oauth_application_id or not row.encrypted_oa_refresh_token:
                return False

            refresh_plain = row.decrypt_oa_refresh_token()
            if not refresh_plain:
                return False

            if (
                not force
                and leeway_seconds is not None
                and row.oa_token_expires_at is not None
                and row.oa_token_expires_at > now + timedelta(seconds=leeway_seconds)
            ):
                return False

            app_secret = row.decrypt_app_secret()
            try:
                token_payload = cls._post_token(
                    app_secret=app_secret,
                    form_body={
                        "refresh_token": refresh_plain,
                        "app_id": row.oauth_application_id,
                        "grant_type": "refresh_token",
                    },
                )
            except Exception:
                logger.warning("Zalo OA token refresh failed channel_id=%s", channel_id, exc_info=True)
                return False

            access_token = str(token_payload.get("access_token") or "")
            if not access_token:
                return False

            new_refresh = str(token_payload.get("refresh_token") or "") or refresh_plain
            expires_in = int(token_payload.get("expires_in") or 90000)
            tenant_id = row.tenant_id

            row.encrypted_page_access_token = encrypter.encrypt_token(tenant_id, access_token)
            row.encrypted_oa_refresh_token = encrypter.encrypt_token(tenant_id, new_refresh)
            row.oa_token_expires_at = naive_utc_now() + timedelta(seconds=max(expires_in - 60, 60))
            session.commit()

        logger.info("Zalo OA token refreshed channel_id=%s", channel_id)
        return True

    @classmethod
    def refresh_due_tokens_batch(cls, lookahead_hours: int = 2) -> dict[str, int]:
        """Periodic job: refresh tokens expiring within lookahead window."""
        threshold = naive_utc_now() + timedelta(hours=lookahead_hours)
        with Session(db.engine, expire_on_commit=False) as session:
            stmt = select(OmniChannelConfig.channel_id).where(
                OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                OmniChannelConfig.enabled.is_(True),
                OmniChannelConfig.encrypted_oa_refresh_token.is_not(None),
                OmniChannelConfig.oauth_application_id.is_not(None),
                or_(
                    OmniChannelConfig.oa_token_expires_at.is_(None),
                    OmniChannelConfig.oa_token_expires_at < threshold,
                ),
            )
            rows = session.scalars(stmt).all()

        refreshed = 0
        for cid in rows:
            if cls.refresh_tokens_for_channel(cid, force=True):
                refreshed += 1
        return {"candidates": len(rows), "refreshed": refreshed}

    @classmethod
    def connection_status(cls, tenant_id: str, channel_id: str) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                    OmniChannelConfig.channel_type == OmniChannelType.ZALO_OA,
                )
            )
        if not row:
            raise ValueError("Zalo channel not found")

        has_access = bool(row.encrypted_page_access_token)
        access_plain = row.decrypt_page_access_token() if has_access else ""
        connected = bool(access_plain.strip())
        oauth_status = "pending_auth"
        if connected:
            oauth_status = "connected"
            if (
                row.oa_token_expires_at
                and row.oa_token_expires_at < naive_utc_now()
                and not row.encrypted_oa_refresh_token
            ):
                oauth_status = "expired"

        return {
            "connected": connected,
            "oauth_status": oauth_status,
            "expires_at": row.oa_token_expires_at.isoformat() if row.oa_token_expires_at else None,
            "oauth_callback_url": cls.public_callback_url(),
        }
