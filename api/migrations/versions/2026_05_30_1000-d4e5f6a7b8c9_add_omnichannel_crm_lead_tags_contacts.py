"""add tags and contact fields to omnichannel_crm_leads

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-30 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("omnichannel_crm_leads", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column("omnichannel_crm_leads", sa.Column("contact_phone", sa.String(length=32), nullable=True))
    op.add_column("omnichannel_crm_leads", sa.Column("contact_email", sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column("omnichannel_crm_leads", "contact_email")
    op.drop_column("omnichannel_crm_leads", "contact_phone")
    op.drop_column("omnichannel_crm_leads", "tags")
