"""Add Mini CRM business_line verticals and member access.

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-07-09 10:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "j6k7l8m9n0o1"
down_revision = "i5j6k7l8m9n0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    config_cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}
    if "mini_crm_business_line" not in config_cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("mini_crm_business_line", sa.String(length=32), nullable=True),
        )

    lead_cols = {col["name"] for col in inspector.get_columns("omnichannel_crm_leads")}
    if "business_line" not in lead_cols:
        op.add_column(
            "omnichannel_crm_leads",
            sa.Column("business_line", sa.String(length=32), nullable=True),
        )
        op.create_index(
            "idx_omni_crm_lead_tenant_business_line",
            "omnichannel_crm_leads",
            ["tenant_id", "business_line"],
        )

    if not inspector.has_table("tenant_account_mini_crm_verticals"):
        op.create_table(
            "tenant_account_mini_crm_verticals",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("account_id", sa.String(length=36), nullable=False),
            sa.Column("business_line", sa.String(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id", name="tenant_account_mini_crm_vertical_pkey"),
            sa.UniqueConstraint(
                "tenant_id",
                "account_id",
                "business_line",
                name="uniq_tenant_account_mini_crm_vertical",
            ),
        )
        op.create_index(
            "idx_tenant_account_mini_crm_vertical_tenant",
            "tenant_account_mini_crm_verticals",
            ["tenant_id", "account_id"],
        )

    op.execute(
        sa.text(
            "UPDATE omnichannel_crm_leads SET business_line = 'restaurant' WHERE business_line IS NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("tenant_account_mini_crm_verticals"):
        op.drop_index("idx_tenant_account_mini_crm_vertical_tenant", table_name="tenant_account_mini_crm_verticals")
        op.drop_table("tenant_account_mini_crm_verticals")

    lead_cols = {col["name"] for col in inspector.get_columns("omnichannel_crm_leads")}
    if "business_line" in lead_cols:
        op.drop_index("idx_omni_crm_lead_tenant_business_line", table_name="omnichannel_crm_leads")
        op.drop_column("omnichannel_crm_leads", "business_line")

    config_cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}
    if "mini_crm_business_line" in config_cols:
        op.drop_column("omnichannel_configs", "mini_crm_business_line")
