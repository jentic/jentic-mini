"""add job durability columns

Adds the visibility-timeout + retry-budget columns the worker needs to recover
jobs orphaned by a dead worker/pod (§09 E4.2):

- ``visible_at``: the claim deadline for a RUNNING job. A RUNNING job whose
  ``visible_at`` has passed is treated as claimable again, so a job left RUNNING
  by a crashed worker is reclaimed rather than stuck forever.
- ``attempts``: how many times the job has been claimed; once it exceeds the
  retry budget a repeatedly-failing job is dead-lettered instead of requeued.

The ``dead_letter`` status value needs no DDL — ``jobs.status`` is a plain
``VARCHAR``, not a Postgres enum, so the new value is accepted as-is.

Revision ID: u0v1w2x3y4z5
Revises: t9u0v1w2x3y4
Create Date: 2026-06-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "u0v1w2x3y4z5"
down_revision: str | None = "t9u0v1w2x3y4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("visible_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_jobs_visible_at", "jobs", ["visible_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_visible_at", table_name="jobs")
    op.drop_column("jobs", "attempts")
    op.drop_column("jobs", "visible_at")
