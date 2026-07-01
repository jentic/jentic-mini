"""add jobs table

Revision ID: 5c42e921d74b
Revises:
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "5c42e921d74b"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    empty_json = sa.text("'{}'::jsonb") if pg else sa.text("'{}'")

    if pg:
        op.execute("""
            CREATE OR REPLACE FUNCTION generate_ksuid(prefix text) RETURNS text
            LANGUAGE sql VOLATILE
            AS $$
                SELECT prefix || '_' ||
                    lpad(to_hex(extract(epoch FROM clock_timestamp())::bigint), 8, '0') ||
                    substr(replace(gen_random_uuid()::text, '-', ''), 1, 16)
            $$
        """)

    op.create_table(
        "jobs",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("job") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "parent_job_id",
            sa.String(30),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "progress",
            json_variant(),
            server_default=empty_json,
            nullable=False,
        ),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("friendly_error", sa.Text, nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("input_metadata", json_variant(), nullable=False),
        sa.Column(
            "results",
            json_variant(),
            server_default=empty_json,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_parent_job_id", "jobs", ["parent_job_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_jobs_created_by", "jobs", ["created_by"])


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.drop_index("ix_jobs_created_by", table_name="jobs")
    op.drop_table("jobs")
    if pg:
        op.execute("DROP FUNCTION IF EXISTS generate_ksuid(text)")
