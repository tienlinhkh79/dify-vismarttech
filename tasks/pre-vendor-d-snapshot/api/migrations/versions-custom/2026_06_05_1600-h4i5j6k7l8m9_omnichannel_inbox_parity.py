"""Omnichannel inbox parity: conversation status, unread, canned responses.

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-06-05 16:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "h4i5j6k7l8m9"
down_revision = "g3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    conv_cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}

    if "status" not in conv_cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        )
    if "assignee_account_id" not in conv_cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("assignee_account_id", sa.String(length=36), nullable=True),
        )
    if "unread_count" not in conv_cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "agent_last_seen_at" not in conv_cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("agent_last_seen_at", sa.DateTime(), nullable=True),
        )
    if "snoozed_until" not in conv_cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        )

    indexes = {idx["name"] for idx in inspector.get_indexes("omnichannel_conversations")}
    if "idx_omni_conversation_tenant_last_msg" not in indexes:
        op.create_index(
            "idx_omni_conversation_tenant_last_msg",
            "omnichannel_conversations",
            ["tenant_id", "last_message_at"],
        )

    if not inspector.has_table("omnichannel_canned_responses"):
        op.create_table(
            "omnichannel_canned_responses",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("shortcut", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id", name="omnichannel_canned_response_pkey"),
        )
        op.create_index("idx_omni_canned_tenant", "omnichannel_canned_responses", ["tenant_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("omnichannel_canned_responses"):
        op.drop_index("idx_omni_canned_tenant", table_name="omnichannel_canned_responses")
        op.drop_table("omnichannel_canned_responses")

    indexes = {idx["name"] for idx in inspector.get_indexes("omnichannel_conversations")}
    if "idx_omni_conversation_tenant_last_msg" in indexes:
        op.drop_index("idx_omni_conversation_tenant_last_msg", table_name="omnichannel_conversations")

    conv_cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}
    for name in ("snoozed_until", "agent_last_seen_at", "unread_count", "assignee_account_id", "status"):
        if name in conv_cols:
            op.drop_column("omnichannel_conversations", name)
