"""Add omnichannel auto-reply policy columns and enable personal defaults.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-06-08 10:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "i5j6k7l8m9n0"
down_revision = "h4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}

    if "auto_reply_pause_when_assigned" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column(
                "auto_reply_pause_when_assigned",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
        )
    if "auto_reply_pause_when_resolved" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column(
                "auto_reply_pause_when_resolved",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
        )
    if "auto_reply_business_hours_enabled" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column(
                "auto_reply_business_hours_enabled",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )
    if "auto_reply_business_hours_start" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("auto_reply_business_hours_start", sa.String(length=5), nullable=True),
        )
    if "auto_reply_business_hours_end" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("auto_reply_business_hours_end", sa.String(length=5), nullable=True),
        )
    if "auto_reply_timezone" not in cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column(
                "auto_reply_timezone",
                sa.String(length=64),
                server_default="Asia/Ho_Chi_Minh",
                nullable=False,
            ),
        )

    op.execute(
        """
        UPDATE omnichannel_configs
        SET zalo_auto_reply_enabled = true
        WHERE channel_type IN ('zalo_personal', 'facebook_messenger', 'instagram_dm')
          AND zalo_auto_reply_enabled = false
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}
    for name in (
        "auto_reply_timezone",
        "auto_reply_business_hours_end",
        "auto_reply_business_hours_start",
        "auto_reply_business_hours_enabled",
        "auto_reply_pause_when_resolved",
        "auto_reply_pause_when_assigned",
    ):
        if name in cols:
            op.drop_column("omnichannel_configs", name)
