"""add execution records

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "execution_records",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("exec") if pg else None,
            nullable=False,
        ),
        sa.Column("toolkit_id", sa.String(30), nullable=False),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("operation_id", sa.String(512), nullable=True),
        sa.Column("api_vendor", sa.String(128), nullable=True),
        sa.Column("api_name", sa.String(128), nullable=True),
        sa.Column("api_version", sa.String(128), nullable=True),
        sa.Column("pinned_revisions", json_variant(), nullable=True),
        sa.Column("http_status", sa.SmallInteger, nullable=True),
        sa.Column("error", sa.String(128), nullable=True),
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
    op.create_index("ix_execution_records_started_at", "execution_records", ["started_at"])
    op.create_index("ix_execution_records_trace_id", "execution_records", ["trace_id"])
    op.create_index(
        "ix_execution_records_toolkit_started",
        "execution_records",
        ["toolkit_id", "started_at"],
    )
    op.create_index("ix_execution_records_status", "execution_records", ["status"])
    op.create_index("ix_execution_records_created_at", "execution_records", ["created_at"])
    op.create_index("ix_execution_records_created_by", "execution_records", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_execution_records_created_by", table_name="execution_records")
    op.drop_index("ix_execution_records_created_at", table_name="execution_records")
    op.drop_table("execution_records")
