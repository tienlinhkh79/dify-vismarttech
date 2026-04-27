"""Create and manage tenant-scoped KiotViet credential connections."""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.tools.tool_manager import ToolManager
from core.helper import encrypter
from extensions.ext_database import db
from models.tools import BuiltinToolProvider
from models.trigger import KiotVietConnection
from services.tools.builtin_tools_manage_service import BuiltinToolManageService


class KiotVietConnectionInput(TypedDict):
    connection_id: str
    name: str
    client_id: str
    client_secret: str
    retailer_name: str
    enabled: bool


class KiotVietConnectionService:
    @staticmethod
    def _sanitize_connection_id(value: str) -> str:
        sanitized = "".join(ch if (ch.isalnum() or ch == "-") else "-" for ch in value.strip().lower())
        while "--" in sanitized:
            sanitized = sanitized.replace("--", "-")
        return sanitized.strip("-")

    @classmethod
    def _ensure_backfilled_from_legacy(cls, session: Session, tenant_id: str, user_id: str | None = None) -> None:
        existing = session.scalar(
            select(KiotVietConnection.id).where(KiotVietConnection.tenant_id == tenant_id).limit(1)
        )
        if existing:
            return

        legacy_provider = session.scalar(
            select(BuiltinToolProvider)
            .where(BuiltinToolProvider.tenant_id == tenant_id, BuiltinToolProvider.provider == "kiotviet")
            .order_by(BuiltinToolProvider.is_default.desc(), BuiltinToolProvider.created_at.asc())
        )
        if not legacy_provider:
            return

        provider_controller = ToolManager.get_builtin_provider("kiotviet", tenant_id)
        provider_encrypter, _ = BuiltinToolManageService.create_tool_encrypter(
            tenant_id=tenant_id,
            db_provider=legacy_provider,
            provider="kiotviet",
            provider_controller=provider_controller,
        )
        decrypted = provider_encrypter.decrypt(legacy_provider.credentials)
        client_id = str(decrypted.get("client_id") or "").strip()
        client_secret = str(decrypted.get("client_secret") or "").strip()
        retailer_name = str(decrypted.get("retailer_name") or "").strip()
        if not client_id or not client_secret or not retailer_name:
            return

        connection_id = cls._sanitize_connection_id(f"kiotviet-{retailer_name}") or "kiotviet-main"
        row = KiotVietConnection(
            tenant_id=tenant_id,
            user_id=user_id or legacy_provider.user_id,
            name=retailer_name,
            connection_id=connection_id,
            client_id=client_id,
            encrypted_client_secret=encrypter.encrypt_token(tenant_id, client_secret),
            retailer_name=retailer_name,
            enabled=True,
        )
        session.add(row)
        session.commit()

    @staticmethod
    def _to_masked_dict(row: KiotVietConnection) -> dict[str, Any]:
        return {
            "id": row.id,
            "platform": "kiotviet",
            "connection_id": row.connection_id,
            "name": row.name,
            "client_id": row.client_id,
            "retailer_name": row.retailer_name,
            "enabled": row.enabled,
            "status": "active" if row.enabled else "inactive",
            "client_secret_masked": encrypter.full_mask_token(),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def list_connections(cls, tenant_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        with Session(db.engine, expire_on_commit=False) as session:
            cls._ensure_backfilled_from_legacy(session, tenant_id, user_id)
            rows = (
                session.query(KiotVietConnection)
                .where(KiotVietConnection.tenant_id == tenant_id)
                .order_by(KiotVietConnection.created_at.desc())
                .all()
            )
        return [cls._to_masked_dict(row) for row in rows]

    @classmethod
    def get_connection(cls, tenant_id: str, connection_id: str) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(KiotVietConnection).where(
                    KiotVietConnection.tenant_id == tenant_id,
                    KiotVietConnection.connection_id == connection_id,
                )
            )
        if not row:
            return None
        return cls._to_masked_dict(row)

    @staticmethod
    def create_connection(tenant_id: str, user_id: str, payload: KiotVietConnectionInput) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            existed = session.scalar(
                select(KiotVietConnection).where(
                    KiotVietConnection.tenant_id == tenant_id,
                    KiotVietConnection.connection_id == payload["connection_id"],
                )
            )
            if existed:
                raise ValueError("Connection ID already exists")

            row = KiotVietConnection(
                tenant_id=tenant_id,
                user_id=user_id,
                name=payload["name"],
                connection_id=payload["connection_id"],
                client_id=payload["client_id"],
                encrypted_client_secret=encrypter.encrypt_token(tenant_id, payload["client_secret"]),
                retailer_name=payload["retailer_name"],
                enabled=payload["enabled"],
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return KiotVietConnectionService._to_masked_dict(row)

    @staticmethod
    def update_connection(tenant_id: str, connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(KiotVietConnection).where(
                    KiotVietConnection.tenant_id == tenant_id,
                    KiotVietConnection.connection_id == connection_id,
                )
            )
            if not row:
                raise ValueError("Connection not found")

            if "name" in payload:
                row.name = payload["name"]
            if "client_id" in payload:
                row.client_id = payload["client_id"]
            if "retailer_name" in payload:
                row.retailer_name = payload["retailer_name"]
            if "enabled" in payload:
                row.enabled = payload["enabled"]
            if "client_secret" in payload:
                row.encrypted_client_secret = encrypter.encrypt_token(tenant_id, payload["client_secret"])

            session.commit()
            session.refresh(row)
            return KiotVietConnectionService._to_masked_dict(row)

    @staticmethod
    def delete_connection(tenant_id: str, connection_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(KiotVietConnection).where(
                    KiotVietConnection.tenant_id == tenant_id,
                    KiotVietConnection.connection_id == connection_id,
                )
            )
            if not row:
                raise ValueError("Connection not found")
            session.delete(row)
            session.commit()
