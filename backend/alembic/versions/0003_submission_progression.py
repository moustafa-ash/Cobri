"""Add auditable tutoring progression fields to submissions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_submission_progression"
down_revision: str | None = "0002_job_lease_owner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("submissions")}
    if "purpose" not in columns:
        op.add_column(
            "submissions",
            sa.Column("purpose", sa.String(16), nullable=False, server_default="assessment"),
        )
    if "parent_submission_id" not in columns:
        op.add_column(
            "submissions", sa.Column("parent_submission_id", sa.String(36), nullable=True)
        )
        op.create_index(
            "ix_submissions_parent_submission_id",
            "submissions",
            ["parent_submission_id"],
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("submissions")}
    if "parent_submission_id" in columns:
        op.drop_index("ix_submissions_parent_submission_id", table_name="submissions")
        op.drop_column("submissions", "parent_submission_id")
    if "purpose" in columns:
        op.drop_column("submissions", "purpose")
