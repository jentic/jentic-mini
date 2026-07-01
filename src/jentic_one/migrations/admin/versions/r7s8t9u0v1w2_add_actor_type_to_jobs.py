"""add actor_type to jobs

Persists the enqueuing actor's type on the job row alongside ``created_by``
(the actor id), so the deferred worker can attribute audit entries without
smuggling the type through the job payload.

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-06-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "r7s8t9u0v1w2"
down_revision: str | None = "q6r7s8t9u0v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("jobs", "actor_type")
