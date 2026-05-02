"""normalize legacy model_type values

Revision ID: b1f2d3e4a5b6
Revises: 9b7c3a1d2e4f
Create Date: 2026-05-01 01:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1f2d3e4a5b6"
down_revision = "9b7c3a1d2e4f"
branch_labels = None
depends_on = None


def _normalize_model_type(table_name: str) -> None:
    op.execute(f"UPDATE {table_name} SET model_type = 'text-embedding' WHERE model_type = 'embeddings'")
    op.execute(f"UPDATE {table_name} SET model_type = 'llm' WHERE model_type = 'text-generation'")
    op.execute(f"UPDATE {table_name} SET model_type = 'rerank' WHERE model_type = 'reranking'")


def upgrade() -> None:
    _normalize_model_type("provider_models")
    _normalize_model_type("provider_model_settings")
    _normalize_model_type("tenant_default_models")
    _normalize_model_type("provider_model_credentials")
    _normalize_model_type("load_balancing_model_configs")


def downgrade() -> None:
    # No-op: old aliases are intentionally retired.
    pass
