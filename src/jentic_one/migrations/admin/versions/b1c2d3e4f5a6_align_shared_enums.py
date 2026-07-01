"""align shared enums

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    if pg:
        op.alter_column("jobs", "type", new_column_name="kind")
        op.alter_column("jobs", "kind", type_=sa.String(16), existing_type=sa.String(20))
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.alter_column(
                "type", new_column_name="kind", type_=sa.String(16), existing_type=sa.String(20)
            )

    op.execute(
        """
        UPDATE jobs SET kind = CASE kind
            WHEN 'PIPELINE' THEN 'execution'
            WHEN 'STAGE' THEN 'execution'
            WHEN 'TRACE' THEN 'execution'
            WHEN 'INGEST' THEN 'import'
            WHEN 'UPLOAD' THEN 'import'
            WHEN 'DELETE' THEN 'execution'
            WHEN 'GROUP' THEN 'execution'
            ELSE 'execution'
        END
        """
    )

    op.execute(
        """
        UPDATE jobs SET status = CASE status
            WHEN 'INITIALIZED' THEN 'queued'
            WHEN 'QUEUED' THEN 'queued'
            WHEN 'RUNNING' THEN 'running'
            WHEN 'SUCCEEDED' THEN 'completed'
            WHEN 'FAILED' THEN 'failed'
            WHEN 'CANCELED' THEN 'cancelled'
            ELSE status
        END
        """
    )


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    op.execute(
        """
        UPDATE jobs SET status = CASE status
            WHEN 'queued' THEN 'QUEUED'
            WHEN 'running' THEN 'RUNNING'
            WHEN 'completed' THEN 'SUCCEEDED'
            WHEN 'failed' THEN 'FAILED'
            WHEN 'cancelled' THEN 'CANCELED'
            ELSE status
        END
        """
    )

    op.execute(
        """
        UPDATE jobs SET kind = CASE kind
            WHEN 'import' THEN 'INGEST'
            WHEN 'execution' THEN 'PIPELINE'
            ELSE 'PIPELINE'
        END
        """
    )

    if pg:
        op.alter_column("jobs", "kind", type_=sa.String(20), existing_type=sa.String(16))
        op.alter_column("jobs", "kind", new_column_name="type")
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.alter_column(
                "kind", new_column_name="type", type_=sa.String(20), existing_type=sa.String(16)
            )
