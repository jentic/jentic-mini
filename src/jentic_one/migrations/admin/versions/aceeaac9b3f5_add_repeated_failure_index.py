"""add_repeated_failure_index

Revision ID: aceeaac9b3f5
Revises: y4z5a6b7c8d9
Create Date: 2026-06-29 11:35:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aceeaac9b3f5"
down_revision: str | None = "y4z5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Partial index to make the Repeated Failure COUNT query an ultra-fast Index-Only Scan
    # even during a failure storm.
    #
    # Build CONCURRENTLY so we never take an exclusive lock on execution_records
    # (which blocks writes while the index builds). Postgres forbids concurrent
    # index builds inside a transaction, so run it in an autocommit block.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_execution_records_repeated_failure_scan",
            "execution_records",
            ["actor_id", "toolkit_id", "operation_id", "started_at"],
            unique=False,
            postgresql_where=sa.text("status = 'failed'"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_execution_records_repeated_failure_scan",
            table_name="execution_records",
            postgresql_where=sa.text("status = 'failed'"),
            postgresql_concurrently=True,
        )
