"""Add append-only learner events and progress projection."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_learner_history"
down_revision: str | None = "0003_submission_progression"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "learner_events" not in existing:
        op.create_table(
            "learner_events",
            sa.Column("event_id", sa.String(36), primary_key=True),
            sa.Column("issuer", sa.String(512), nullable=False),
            sa.Column("subject", sa.String(512), nullable=False),
            sa.Column("session_id", sa.String(36), nullable=False),
            sa.Column("submission_id", sa.String(36), nullable=True),
            sa.Column("event_type", sa.String(32), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_learner_events_owner", "learner_events", ["issuer", "subject", "created_at"]
        )
    if "learner_progress" not in existing:
        op.create_table(
            "learner_progress",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("issuer", sa.String(512), nullable=False),
            sa.Column("subject", sa.String(512), nullable=False),
            sa.Column("content_package_id", sa.String(128), nullable=False),
            sa.Column("content_version", sa.String(128), nullable=False),
            sa.Column("item_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="started"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "issuer", "subject", "content_package_id", "content_version", "item_id"
            ),
        )


def downgrade() -> None:
    op.drop_table("learner_progress")
    op.drop_index("ix_learner_events_owner", table_name="learner_events")
    op.drop_table("learner_events")
