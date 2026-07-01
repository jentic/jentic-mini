"""add events

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    empty_json = sa.text("'{}'::jsonb") if pg else sa.text("'{}'")
    op.create_table(
        "events",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("evt") if pg else None,
            nullable=False,
        ),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("requires_action", sa.Boolean, server_default="false", nullable=False),
        sa.Column("acknowledged", sa.Boolean, server_default="false", nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(30), nullable=True),
        sa.Column("acknowledgement_note", sa.Text, nullable=True),
        sa.Column("trace_id", sa.String(32), nullable=True),
        sa.Column("summary", sa.String(512), nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column(
            "data",
            json_variant(),
            server_default=empty_json,
            nullable=False,
        ),
        sa.Column("execution_id", sa.String(30), nullable=True),
        sa.Column("job_id", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_type_created", "events", ["type", "created_at"])
    op.create_index("ix_events_severity_created", "events", ["severity", "created_at"])
    op.create_index(
        "ix_events_requires_action_unack",
        "events",
        ["requires_action"],
        postgresql_where=sa.text("requires_action AND NOT acknowledged"),
        sqlite_where=sa.text("requires_action = 1 AND acknowledged = 0"),
    )
    op.create_index(
        "ix_events_trace_id",
        "events",
        ["trace_id"],
        postgresql_where=sa.text("trace_id IS NOT NULL"),
        sqlite_where=sa.text("trace_id IS NOT NULL"),
    )
    op.create_index("ix_events_created_by", "events", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_events_created_by", table_name="events")
    op.drop_table("events")
