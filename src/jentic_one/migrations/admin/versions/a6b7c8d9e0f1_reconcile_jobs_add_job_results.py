"""reconcile jobs add job results

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    empty_json = sa.text("'{}'::jsonb") if pg else sa.text("'{}'")

    if pg:
        # Drop unused columns from jobs.
        op.drop_column("jobs", "name")
        op.drop_column("jobs", "progress")
        op.drop_column("jobs", "friendly_error")
        op.drop_column("jobs", "start_time")
        op.drop_column("jobs", "end_time")
        op.drop_column("jobs", "input_metadata")
        op.drop_column("jobs", "results")

        # Alter error column from Text to String(128).
        op.alter_column(
            "jobs",
            "error",
            type_=sa.String(128),
            existing_type=sa.Text,
            existing_nullable=True,
        )

        # Add new columns.
        op.add_column("jobs", sa.Column("execution_id", sa.String(30), nullable=True))
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.drop_column("name")
            batch.drop_column("progress")
            batch.drop_column("friendly_error")
            batch.drop_column("start_time")
            batch.drop_column("end_time")
            batch.drop_column("input_metadata")
            batch.drop_column("results")
            batch.alter_column(
                "error",
                type_=sa.String(128),
                existing_type=sa.Text,
                existing_nullable=True,
            )
            batch.add_column(sa.Column("execution_id", sa.String(30), nullable=True))

    # Create job_results table.
    op.create_table(
        "job_results",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("jres") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.String(30),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "body",
            json_variant(),
            server_default=empty_json,
            nullable=False,
        ),
        sa.Column("available_until", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_job_results_available_until", "job_results", ["available_until"])
    op.create_index("ix_job_results_created_at", "job_results", ["created_at"])
    op.create_index("ix_job_results_created_by", "job_results", ["created_by"])


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    empty_json = sa.text("'{}'::jsonb") if pg else sa.text("'{}'")

    op.drop_index("ix_job_results_created_by", table_name="job_results")
    op.drop_index("ix_job_results_created_at", table_name="job_results")
    op.drop_table("job_results")

    if pg:
        op.drop_column("jobs", "execution_id")

        op.alter_column(
            "jobs",
            "error",
            type_=sa.Text,
            existing_type=sa.String(128),
            existing_nullable=True,
        )

        op.add_column("jobs", sa.Column("name", sa.String(255), nullable=False, server_default=""))
        op.add_column(
            "jobs",
            sa.Column(
                "progress",
                json_variant(),
                server_default=empty_json,
                nullable=False,
            ),
        )
        op.add_column("jobs", sa.Column("friendly_error", sa.Text, nullable=True))
        op.add_column("jobs", sa.Column("start_time", sa.DateTime(timezone=True), nullable=True))
        op.add_column("jobs", sa.Column("end_time", sa.DateTime(timezone=True), nullable=True))
        op.add_column(
            "jobs",
            sa.Column(
                "input_metadata",
                json_variant(),
                nullable=False,
                server_default=empty_json,
            ),
        )
        op.add_column(
            "jobs",
            sa.Column(
                "results",
                json_variant(),
                server_default=empty_json,
                nullable=True,
            ),
        )
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.drop_column("execution_id")
            batch.alter_column(
                "error",
                type_=sa.Text,
                existing_type=sa.String(128),
                existing_nullable=True,
            )
            batch.add_column(sa.Column("name", sa.String(255), nullable=False, server_default=""))
            batch.add_column(
                sa.Column("progress", json_variant(), server_default=empty_json, nullable=False)
            )
            batch.add_column(sa.Column("friendly_error", sa.Text, nullable=True))
            batch.add_column(sa.Column("start_time", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(sa.Column("end_time", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(
                sa.Column(
                    "input_metadata", json_variant(), nullable=False, server_default=empty_json
                )
            )
            batch.add_column(
                sa.Column("results", json_variant(), server_default=empty_json, nullable=True)
            )
