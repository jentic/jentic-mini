"""add setup sentinel

Revision ID: w2x3y4z5a6b7
Revises: 24852503fc19
Create Date: 2026-06-25

Adds a single-row ``setup_sentinels`` table whose fixed primary key serializes
first-admin creation. ``AuthService.bootstrap_admin`` inserts the sentinel row
inside the same transaction that creates the first user; a second concurrent
caller — even one using a *different* email — collides on the primary key and
is rejected. The empty-users ``COUNT(*)`` check alone cannot serialize this
under READ COMMITTED (no range lock), and the unique email index only stops
same-email races, so two land-grab callers with distinct emails could otherwise
both create an ``org:admin`` account.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "w2x3y4z5a6b7"
down_revision: str | None = "24852503fc19"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "setup_sentinels",
        # Fixed-value PK: only the row id == "singleton" is ever inserted, so the
        # second concurrent first-admin attempt trips the primary-key uniqueness.
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Deliberately NO seed row: an empty table is the first-run signal. The row is
    # written at runtime by bootstrap_admin when the first admin is created.


def downgrade() -> None:
    op.drop_table("setup_sentinels")
