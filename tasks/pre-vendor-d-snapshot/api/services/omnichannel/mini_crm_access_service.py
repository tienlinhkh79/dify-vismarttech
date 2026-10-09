"""Mini CRM vertical access control for workspace members."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.account import TenantAccountMiniCrmVertical, TenantAccountRole
from models.engine import db
from models.trigger import MiniCrmBusinessLine

_ALL_VERTICALS = (
    MiniCrmBusinessLine.RESTAURANT.value,
    MiniCrmBusinessLine.NAIL.value,
)


class MiniCrmAccessService:
    @staticmethod
    def normalize_vertical(value: str | None) -> str | None:
        return MiniCrmBusinessLine.normalize(value)

    @classmethod
    def is_privileged_role(cls, role: TenantAccountRole | str | None) -> bool:
        if role is None:
            return False
        try:
            parsed = role if isinstance(role, TenantAccountRole) else TenantAccountRole(str(role))
        except ValueError:
            return False
        return TenantAccountRole.is_privileged_role(parsed)

    @classmethod
    def list_verticals_for_member(cls, *, tenant_id: str, account_id: str) -> list[str]:
        with Session(db.engine, expire_on_commit=False) as session:
            rows = session.scalars(
                select(TenantAccountMiniCrmVertical.business_line).where(
                    TenantAccountMiniCrmVertical.tenant_id == tenant_id,
                    TenantAccountMiniCrmVertical.account_id == account_id,
                )
            ).all()
        verticals = [str(line) for line in rows if str(line).strip()]
        return sorted(dict.fromkeys(verticals))

    @classmethod
    def list_accessible_verticals(
        cls,
        *,
        tenant_id: str,
        account_id: str,
        role: TenantAccountRole | str | None,
    ) -> list[str]:
        if cls.is_privileged_role(role):
            return sorted(_ALL_VERTICALS)
        assigned = cls.list_verticals_for_member(tenant_id=tenant_id, account_id=account_id)
        if assigned:
            return assigned
        # Backward compatibility: members without explicit rows see all verticals.
        return sorted(_ALL_VERTICALS)

    @classmethod
    def can_access_vertical(
        cls,
        *,
        tenant_id: str,
        account_id: str,
        role: TenantAccountRole | str | None,
        business_line: str,
    ) -> bool:
        normalized = cls.normalize_vertical(business_line)
        if not normalized:
            return False
        return normalized in cls.list_accessible_verticals(
            tenant_id=tenant_id,
            account_id=account_id,
            role=role,
        )

    @classmethod
    def set_member_verticals(
        cls,
        *,
        tenant_id: str,
        account_id: str,
        verticals: list[str],
    ) -> list[str]:
        normalized: list[str] = []
        for item in verticals:
            line = cls.normalize_vertical(item)
            if line and line not in normalized:
                normalized.append(line)

        with Session(db.engine, expire_on_commit=False) as session:
            session.execute(
                delete(TenantAccountMiniCrmVertical).where(
                    TenantAccountMiniCrmVertical.tenant_id == tenant_id,
                    TenantAccountMiniCrmVertical.account_id == account_id,
                )
            )
            for line in normalized:
                session.add(
                    TenantAccountMiniCrmVertical(
                        tenant_id=tenant_id,
                        account_id=account_id,
                        business_line=line,
                    )
                )
            session.commit()
        return normalized

    @classmethod
    def verticals_by_account_ids(cls, *, tenant_id: str, account_ids: list[str]) -> dict[str, list[str]]:
        if not account_ids:
            return {}
        with Session(db.engine, expire_on_commit=False) as session:
            rows = session.scalars(
                select(TenantAccountMiniCrmVertical).where(
                    TenantAccountMiniCrmVertical.tenant_id == tenant_id,
                    TenantAccountMiniCrmVertical.account_id.in_(account_ids),
                )
            ).all()
        result: dict[str, list[str]] = {account_id: [] for account_id in account_ids}
        for row in rows:
            bucket = result.setdefault(row.account_id, [])
            if row.business_line not in bucket:
                bucket.append(row.business_line)
        for account_id, lines in result.items():
            result[account_id] = sorted(lines)
        return result
