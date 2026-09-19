"""Persist immutable evaluation provenance."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_evaluation_provenance"
down_revision: str | None = "0006_quarantined_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("evaluations")}
    if "provenance" not in columns:
        op.add_column("evaluations", sa.Column("provenance", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("evaluations")}
    if "provenance" in columns:
        op.drop_column("evaluations", "provenance")
