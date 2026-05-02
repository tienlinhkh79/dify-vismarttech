"""add participant display fields to omnichannel conversations

Revision ID: f4e8c9a0b1d2
Revises: e7f8a9b0c1d2
Create Date: 2026-05-02 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f4e8c9a0b1d2"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}
    if "participant_display_name" not in cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("participant_display_name", sa.String(length=512), nullable=True),
        )
    if "participant_profile_pic_url" not in cols:
        op.add_column(
            "omnichannel_conversations",
            sa.Column("participant_profile_pic_url", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("omnichannel_conversations")}
    if "participant_profile_pic_url" in cols:
        op.drop_column("omnichannel_conversations", "participant_profile_pic_url")
    if "participant_display_name" in cols:
        op.drop_column("omnichannel_conversations", "participant_display_name")
