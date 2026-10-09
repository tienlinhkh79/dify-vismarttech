"""add last_message_preview to omnichannel conversations

Revision ID: o2b3c4d5e6f7
Revises: o1a2b3c4d5e6
Create Date: 2026-05-12 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "o2b3c4d5e6f7"
down_revision = "o1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}
    if "last_message_preview" not in cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("last_message_preview", sa.String(length=512), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}
    if "last_message_preview" in cols:
        op.drop_column("omnichannel_conversations", "last_message_preview")
