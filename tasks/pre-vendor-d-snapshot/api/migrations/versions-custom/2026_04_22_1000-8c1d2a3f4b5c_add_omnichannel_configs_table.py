"""add omnichannel configs table

Revision ID: 8c1d2a3f4b5c
Revises: 288345cd01d1
Create Date: 2026-04-22 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import models

# revision identifiers, used by Alembic.
revision = "8c1d2a3f4b5c"
down_revision = "288345cd01d1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("omnichannel_configs"):
        op.create_table(
            "omnichannel_configs",
            sa.Column("id", models.types.StringUUID, nullable=False),
            sa.Column("tenant_id", models.types.StringUUID, nullable=False),
            sa.Column("app_id", models.types.StringUUID, nullable=False),
            sa.Column("user_id", models.types.StringUUID, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("channel_type", sa.String(length=60), nullable=False),
            sa.Column("channel_id", sa.String(length=255), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("page_id", sa.String(length=255), nullable=False),
            sa.Column("graph_api_version", sa.String(length=32), nullable=False, server_default=sa.text("'v23.0'")),
            sa.Column("encrypted_verify_token", models.types.LongText, nullable=False),
            sa.Column("encrypted_app_secret", models.types.LongText, nullable=False),
            sa.Column("encrypted_page_access_token", models.types.LongText, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="omnichannel_config_pkey"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("omnichannel_configs")}
    if "idx_omnichannel_tenant_type" not in existing_indexes:
        op.create_index("idx_omnichannel_tenant_type", "omnichannel_configs", ["tenant_id", "channel_type"], unique=False)
    if "idx_omnichannel_channel_id" not in existing_indexes:
        op.create_index("idx_omnichannel_channel_id", "omnichannel_configs", ["channel_id"], unique=True)


def downgrade():
    op.drop_index("idx_omnichannel_channel_id", table_name="omnichannel_configs")
    op.drop_index("idx_omnichannel_tenant_type", table_name="omnichannel_configs")
    op.drop_table("omnichannel_configs")

