"""add omnichannel inbox and sync jobs

Revision ID: 1a9f4d2c7b10
Revises: fce013ca180e
Create Date: 2026-04-30 21:56:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1a9f4d2c7b10"
down_revision = "fce013ca180e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "omnichannel_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=60), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_conversation_pkey"),
        sa.UniqueConstraint("tenant_id", "channel_id", "external_user_id", name="uniq_omni_conversation_user_channel"),
    )
    op.create_index(
        "idx_omni_conversation_tenant_channel", "omnichannel_conversations", ["tenant_id", "channel_id"], unique=False
    )
    op.create_index(
        "idx_omni_conversation_external_user",
        "omnichannel_conversations",
        ["tenant_id", "external_user_id"],
        unique=False,
    )

    op.create_table(
        "omnichannel_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=60), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("direction", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_message_pkey"),
    )
    op.create_index(
        "idx_omni_message_tenant_channel_created",
        "omnichannel_messages",
        ["tenant_id", "channel_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_omni_message_conversation_created",
        "omnichannel_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_omni_message_external_message",
        "omnichannel_messages",
        ["tenant_id", "channel_id", "external_message_id"],
        unique=False,
    )

    op.create_table(
        "omnichannel_sync_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=60), nullable=False),
        sa.Column("since_at", sa.DateTime(), nullable=True),
        sa.Column("until_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("total_messages", sa.Integer(), nullable=False),
        sa.Column("synced_messages", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="omnichannel_sync_job_pkey"),
    )
    op.create_index("idx_omni_sync_job_tenant_channel", "omnichannel_sync_jobs", ["tenant_id", "channel_id"], unique=False)
    op.create_index("idx_omni_sync_job_status_created", "omnichannel_sync_jobs", ["status", "created_at"], unique=False)


def downgrade():
    op.drop_index("idx_omni_sync_job_status_created", table_name="omnichannel_sync_jobs")
    op.drop_index("idx_omni_sync_job_tenant_channel", table_name="omnichannel_sync_jobs")
    op.drop_table("omnichannel_sync_jobs")

    op.drop_index("idx_omni_message_external_message", table_name="omnichannel_messages")
    op.drop_index("idx_omni_message_conversation_created", table_name="omnichannel_messages")
    op.drop_index("idx_omni_message_tenant_channel_created", table_name="omnichannel_messages")
    op.drop_table("omnichannel_messages")

    op.drop_index("idx_omni_conversation_external_user", table_name="omnichannel_conversations")
    op.drop_index("idx_omni_conversation_tenant_channel", table_name="omnichannel_conversations")
    op.drop_table("omnichannel_conversations")
