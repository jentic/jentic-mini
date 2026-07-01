"""add origin column to execution_records

Stores which surface initiated each execution (cli, dashboard, api, agent, system)
so operators can filter execution records by request origin.

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "y4z5a6b7c8d9"
down_revision: str | None = "x3y4z5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_records", sa.Column("origin", sa.String(20), nullable=True))
    op.create_index("ix_execution_records_origin", "execution_records", ["origin", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_execution_records_origin", table_name="execution_records")
    op.drop_column("execution_records", "origin")
