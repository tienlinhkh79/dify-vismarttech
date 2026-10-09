"""merge omnichannel head with upstream 1.15.0 head

Revision ID: l8m9n0o1p2q3
Revises: k7l8m9n0o1p2, d9e8f7a6b5c4
Create Date: 2026-08-26 23:00:00.000000

"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "l8m9n0o1p2q3"
down_revision = ("k7l8m9n0o1p2", "d9e8f7a6b5c4")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
