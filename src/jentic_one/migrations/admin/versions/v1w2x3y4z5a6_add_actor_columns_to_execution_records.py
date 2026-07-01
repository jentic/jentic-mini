"""add actor_id and actor_type columns to execution_records

Surfaces per-execution actor attribution so the execution feed can be filtered
by the agent/user that initiated each execution.

Revision ID: v1w2x3y4z5a6
Revises: u0v1w2x3y4z5
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v1w2x3y4z5a6"
down_revision: str | None = "u0v1w2x3y4z5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_records", sa.Column("actor_id", sa.String(255), nullable=False))
    op.add_column("execution_records", sa.Column("actor_type", sa.String(20), nullable=False))
    op.create_index("ix_execution_records_actor", "execution_records", ["actor_id", "actor_type"])


def downgrade() -> None:
    op.drop_index("ix_execution_records_actor", table_name="execution_records")
    op.drop_column("execution_records", "actor_type")
    op.drop_column("execution_records", "actor_id")
