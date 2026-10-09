"""merge omnichannel/1.15 head with upstream 1.16.1 head

Revision ID: m9n0o1p2q3r4
Revises: l8m9n0o1p2q3, 6f5a9c2d8e1b
Create Date: 2026-08-26 23:50:00.000000

"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "m9n0o1p2q3r4"
down_revision = ("l8m9n0o1p2q3", "6f5a9c2d8e1b")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
