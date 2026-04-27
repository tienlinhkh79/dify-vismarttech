"""add kiotviet connections table

Revision ID: c2d4e6f8a9b1
Revises: 8c1d2a3f4b5c
Create Date: 2026-04-27 11:00:00

"""

from alembic import op
import sqlalchemy as sa

from models.types import LongText, StringUUID

# revision identifiers, used by Alembic.
revision = "c2d4e6f8a9b1"
down_revision = "6b5f9f8b1a2c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kiotviet_connections",
        sa.Column("id", StringUUID, nullable=False),
        sa.Column("tenant_id", StringUUID, nullable=False),
        sa.Column("user_id", StringUUID, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connection_id", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_client_secret", LongText, nullable=False),
        sa.Column("retailer_name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="kiotviet_connection_pkey"),
    )
    op.create_index("idx_kiotviet_tenant", "kiotviet_connections", ["tenant_id"], unique=False)
    op.create_index(
        "idx_kiotviet_tenant_connection_id",
        "kiotviet_connections",
        ["tenant_id", "connection_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("idx_kiotviet_tenant_connection_id", table_name="kiotviet_connections")
    op.drop_index("idx_kiotviet_tenant", table_name="kiotviet_connections")
    op.drop_table("kiotviet_connections")
