"""Add explicit ownership to evaluation job leases."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_job_lease_owner"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("evaluation_jobs")
    }
    if "lease_owner" not in columns:
        op.add_column("evaluation_jobs", sa.Column("lease_owner", sa.String(128), nullable=True))


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("evaluation_jobs")
    }
    if "lease_owner" in columns:
        op.drop_column("evaluation_jobs", "lease_owner")
