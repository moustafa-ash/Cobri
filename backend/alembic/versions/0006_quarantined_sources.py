"""Persist curator-quarantined official source metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_quarantined_sources"
down_revision: str | None = "0005_content_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "quarantined_sources" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "quarantined_sources",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="quarantined"),
    )


def downgrade() -> None:
    if "quarantined_sources" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("quarantined_sources")
