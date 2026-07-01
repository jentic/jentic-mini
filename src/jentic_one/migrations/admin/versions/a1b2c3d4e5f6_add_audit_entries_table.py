"""add audit_entries table

Revision ID: a1b2c3d4e5f6
Revises: 5c42e921d74b
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5c42e921d74b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "audit_entries",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("aud") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("actor_session_id", sa.String(255), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("target_parent_id", sa.String(255), nullable=True),
        sa.Column("before", json_variant(), nullable=True),
        sa.Column("after", json_variant(), nullable=True),
        sa.Column("diff", json_variant(), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        sa.Column("job_id", sa.String(30), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_target",
        "audit_entries",
        ["target_type", "target_id", "occurred_at"],
    )
    op.create_index("ix_audit_actor", "audit_entries", ["actor_id", "occurred_at"])
    op.create_index("ix_audit_occurred_at", "audit_entries", ["occurred_at"])
    op.create_index(
        "ix_audit_trace",
        "audit_entries",
        ["trace_id"],
        postgresql_where=sa.text("trace_id IS NOT NULL"),
        sqlite_where=sa.text("trace_id IS NOT NULL"),
    )
    op.create_index("ix_audit_entries_created_at", "audit_entries", ["created_at"])
    op.create_index("ix_audit_entries_created_by", "audit_entries", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_audit_entries_created_by", table_name="audit_entries")
    op.drop_index("ix_audit_entries_created_at", table_name="audit_entries")
    op.drop_table("audit_entries")
