"""add omnichannel_crm_leads for mini CRM

Revision ID: a1b2c3d4e5f6
Revises: f4e8c9a0b1d2
Create Date: 2026-05-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f4e8c9a0b1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "omnichannel_crm_leads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("owner_account_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_override", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_crm_lead_pkey"),
        sa.UniqueConstraint("tenant_id", "conversation_id", name="uniq_omni_crm_lead_tenant_conversation"),
    )
    op.create_index(
        "idx_omni_crm_lead_tenant_stage",
        "omnichannel_crm_leads",
        ["tenant_id", "stage"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_omni_crm_lead_tenant_stage", table_name="omnichannel_crm_leads")
    op.drop_index("idx_omni_crm_lead_tenant_conversation", table_name="omnichannel_crm_leads")
    op.drop_table("omnichannel_crm_leads")
