"""Create the Day 1 durable workflow tables."""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from cobri.persistence.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from cobri.persistence.models import Base

    Base.metadata.drop_all(bind=op.get_bind())
