"""Store versioned local retrieval vectors."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_content_embeddings"
down_revision: str | None = "0004_learner_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "content_embeddings" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "content_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content_package_id", sa.String(128), nullable=False),
        sa.Column("content_version", sa.String(128), nullable=False),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("package_digest", sa.String(64), nullable=False),
        sa.Column("model_revision", sa.String(256), nullable=False),
        sa.Column("tokenizer_revision", sa.String(256), nullable=False, server_default=""),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("normalized", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.UniqueConstraint("content_package_id", "content_version", "item_id", "model_revision"),
    )


def downgrade() -> None:
    if "content_embeddings" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("content_embeddings")
