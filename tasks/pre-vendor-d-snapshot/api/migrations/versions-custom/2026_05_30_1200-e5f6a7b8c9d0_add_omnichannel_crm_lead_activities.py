"""add omnichannel_crm_lead_activities for Mini CRM timeline

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-30 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "omnichannel_crm_lead_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("actor_account_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_crm_lead_activity_pkey"),
    )
    op.create_index(
        "idx_omni_crm_activity_tenant_conversation",
        "omnichannel_crm_lead_activities",
        ["tenant_id", "conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_omni_crm_activity_tenant_conversation", table_name="omnichannel_crm_lead_activities")
    op.drop_table("omnichannel_crm_lead_activities")
