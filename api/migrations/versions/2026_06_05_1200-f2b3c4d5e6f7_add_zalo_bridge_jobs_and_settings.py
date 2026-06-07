"""add zalo bridge job queue, message_map columns, auto_reply flag

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-05 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import models

revision = "f2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    oc_cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}
    if "zalo_auto_reply_enabled" not in oc_cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("zalo_auto_reply_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )

    map_cols = {col["name"] for col in inspector.get_columns("omnichannel_zalo_message_maps")}
    if "zalo_thread_id" not in map_cols:
        op.add_column(
            "omnichannel_zalo_message_maps", sa.Column("zalo_thread_id", sa.String(length=255), nullable=True)
        )
    if "quote_zalo_msg_id" not in map_cols:
        op.add_column(
            "omnichannel_zalo_message_maps", sa.Column("quote_zalo_msg_id", sa.String(length=255), nullable=True)
        )

    if "omnichannel_zalo_jobs" not in inspector.get_table_names():
        op.create_table(
            "omnichannel_zalo_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("channel_id", sa.String(length=255), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("dedup_key", sa.String(length=512), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("max_attempts", sa.Integer(), server_default="8", nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("last_error", models.types.LongText, nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id", name="omnichannel_zalo_job_pkey"),
            sa.UniqueConstraint("kind", "dedup_key", name="uniq_omni_zalo_job_dedup"),
        )
        op.create_index(
            "idx_omni_zalo_job_status_next",
            "omnichannel_zalo_jobs",
            ["status", "next_attempt_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "omnichannel_zalo_jobs" in inspector.get_table_names():
        op.drop_index("idx_omni_zalo_job_status_next", table_name="omnichannel_zalo_jobs")
        op.drop_table("omnichannel_zalo_jobs")
    map_cols = {col["name"] for col in inspector.get_columns("omnichannel_zalo_message_maps")}
    if "quote_zalo_msg_id" in map_cols:
        op.drop_column("omnichannel_zalo_message_maps", "quote_zalo_msg_id")
    if "zalo_thread_id" in map_cols:
        op.drop_column("omnichannel_zalo_message_maps", "zalo_thread_id")
    oc_cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}
    if "zalo_auto_reply_enabled" in oc_cols:
        op.drop_column("omnichannel_configs", "zalo_auto_reply_enabled")
