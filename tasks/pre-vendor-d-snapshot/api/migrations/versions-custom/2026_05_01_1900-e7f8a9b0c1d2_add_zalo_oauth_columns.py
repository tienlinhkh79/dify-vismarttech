"""add zalo oauth columns to omnichannel_configs

Revision ID: e7f8a9b0c1d2
Revises: b1f2d3e4a5b6
Create Date: 2026-05-01 19:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

import models

# revision identifiers, used by Alembic.
revision = "e7f8a9b0c1d2"
down_revision = "b1f2d3e4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    oc_cols = {col["name"] for col in inspector.get_columns("omnichannel_configs")}

    if "oauth_application_id" not in oc_cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("oauth_application_id", sa.String(length=255), nullable=True),
        )

    if "encrypted_oa_refresh_token" not in oc_cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("encrypted_oa_refresh_token", models.types.LongText, nullable=True),
        )

    if "oa_token_expires_at" not in oc_cols:
        op.add_column(
            "omnichannel_configs",
            sa.Column("oa_token_expires_at", sa.DateTime(), nullable=True),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("omnichannel_configs")}
    if "idx_omnichannel_zalo_token_expires" not in existing_indexes:
        op.create_index(
            "idx_omnichannel_zalo_token_expires",
            "omnichannel_configs",
            ["oa_token_expires_at"],
            unique=False,
        )

    op.alter_column(
        "omnichannel_configs",
        "encrypted_page_access_token",
        existing_type=models.types.LongText,
        nullable=True,
    )


def downgrade() -> None:
    op.drop_index("idx_omnichannel_zalo_token_expires", table_name="omnichannel_configs")
    op.drop_column("omnichannel_configs", "oa_token_expires_at")
    op.drop_column("omnichannel_configs", "encrypted_oa_refresh_token")
    op.drop_column("omnichannel_configs", "oauth_application_id")
    op.alter_column(
        "omnichannel_configs",
        "encrypted_page_access_token",
        existing_type=models.types.LongText,
        nullable=False,
    )
