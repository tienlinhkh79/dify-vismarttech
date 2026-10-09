"""Unit tests for MiniCrmAccessService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from models.account import TenantAccountRole
from services.omnichannel.mini_crm_access_service import MiniCrmAccessService


class TestMiniCrmAccessService:
    def test_privileged_role_sees_all_verticals(self):
        verticals = MiniCrmAccessService.list_accessible_verticals(
            tenant_id="tenant-1",
            account_id="account-1",
            role=TenantAccountRole.ADMIN,
        )
        assert verticals == ["nail", "restaurant"]

    def test_assigned_verticals_only(self):
        with patch.object(
            MiniCrmAccessService,
            "list_verticals_for_member",
            return_value=["nail"],
        ):
            verticals = MiniCrmAccessService.list_accessible_verticals(
                tenant_id="tenant-1",
                account_id="account-1",
                role=TenantAccountRole.NORMAL,
            )
        assert verticals == ["nail"]

    def test_empty_assignment_falls_back_to_all(self):
        with patch.object(
            MiniCrmAccessService,
            "list_verticals_for_member",
            return_value=[],
        ):
            verticals = MiniCrmAccessService.list_accessible_verticals(
                tenant_id="tenant-1",
                account_id="account-1",
                role=TenantAccountRole.EDITOR,
            )
        assert verticals == ["nail", "restaurant"]

    def test_can_access_vertical(self):
        with patch.object(
            MiniCrmAccessService,
            "list_accessible_verticals",
            return_value=["restaurant"],
        ):
            assert MiniCrmAccessService.can_access_vertical(
                tenant_id="tenant-1",
                account_id="account-1",
                role=TenantAccountRole.NORMAL,
                business_line="restaurant",
            )
            assert not MiniCrmAccessService.can_access_vertical(
                tenant_id="tenant-1",
                account_id="account-1",
                role=TenantAccountRole.NORMAL,
                business_line="nail",
            )

    def test_normalize_vertical(self):
        assert MiniCrmAccessService.normalize_vertical("Restaurant") == "restaurant"
        assert MiniCrmAccessService.normalize_vertical("invalid") is None

    def test_set_member_verticals_dedupes(self):
        session = MagicMock()
        session_cm = MagicMock()
        session_cm.__enter__.return_value = session
        session_cm.__exit__.return_value = False

        with patch("services.omnichannel.mini_crm_access_service.db") as mock_db:
            mock_db.engine = MagicMock()
            with patch(
                "services.omnichannel.mini_crm_access_service.Session",
                return_value=session_cm,
            ):
                result = MiniCrmAccessService.set_member_verticals(
                    tenant_id="tenant-1",
                    account_id="account-1",
                    verticals=["restaurant", "restaurant", "nail", "bad"],
                )

        assert result == ["restaurant", "nail"]
        session.commit.assert_called_once()
