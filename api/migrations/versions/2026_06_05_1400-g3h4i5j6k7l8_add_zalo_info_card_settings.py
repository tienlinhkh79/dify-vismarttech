"""Add Zalo OA info-card settings on omnichannel_configs.

Revision ID: g3h4i5j6k7l8
Revises: f2b3c4d5e6f7
Create Date: 2026-06-05 14:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "g3h4i5j6k7l8"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_configs")}
    if "zalo_info_card_enabled" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("zalo_info_card_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "zalo_info_card_title" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("zalo_info_card_title", sa.String(length=255), nullable=True),
        )
    if "zalo_info_card_subtitle" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("zalo_info_card_subtitle", sa.String(length=512), nullable=True),
        )
    if "zalo_info_card_image_url" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("zalo_info_card_image_url", sa.String(length=2048), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_configs")}
    for name in (
        "zalo_info_card_image_url",
        "zalo_info_card_subtitle",
        "zalo_info_card_title",
        "zalo_info_card_enabled",
    ):
        if name in cols:
            op.drop_column("omnichannel_configs", name)
