"""add omnichannel_zalo_message_maps for Zalo OA echo suppression

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-06-05 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "omnichannel_zalo_message_maps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("zalo_msg_id", sa.String(length=255), nullable=False),
        sa.Column("omnichannel_message_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_zalo_message_map_pkey"),
        sa.UniqueConstraint("channel_id", "zalo_msg_id", name="uniq_omni_zalo_msg_map"),
    )
    op.create_index(
        "idx_omni_zalo_msg_map_message",
        "omnichannel_zalo_message_maps",
        ["omnichannel_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_omni_zalo_msg_map_message", table_name="omnichannel_zalo_message_maps")
    op.drop_table("omnichannel_zalo_message_maps")
