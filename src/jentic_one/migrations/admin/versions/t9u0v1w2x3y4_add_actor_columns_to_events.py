"""add actor_id and actor_type columns to events

Surfaces per-event actor attribution so the event feed can be filtered by
the agent/user that caused each event.

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "t9u0v1w2x3y4"
down_revision: str | None = "s8t9u0v1w2x3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("actor_id", sa.String(255), nullable=True))
    op.add_column("events", sa.Column("actor_type", sa.String(20), nullable=True))
    op.create_index("ix_events_actor", "events", ["actor_id", "actor_type"])


def downgrade() -> None:
    op.drop_index("ix_events_actor", table_name="events")
    op.drop_column("events", "actor_type")
    op.drop_column("events", "actor_id")
