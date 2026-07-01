"""add server_variables to credentials

Revision ID: g8b9c0d1e2f3
Revises: a2b3c4d5e6f7
Create Date: 2026-06-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g8b9c0d1e2f3"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "credentials",
        sa.Column(
            "server_variables",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("credentials", "server_variables")
