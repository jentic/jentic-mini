"""add payload column and widen error to text

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "h7i8j9k0l1m2"
down_revision: str | None = "g6h7i8j9k0l1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    if pg:
        op.add_column("jobs", sa.Column("payload", json_variant(), nullable=True))
        op.alter_column(
            "jobs",
            "error",
            type_=sa.Text,
            existing_type=sa.String(128),
            existing_nullable=True,
        )
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.add_column(sa.Column("payload", json_variant(), nullable=True))
            batch.alter_column(
                "error",
                type_=sa.Text,
                existing_type=sa.String(128),
                existing_nullable=True,
            )


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    if pg:
        op.alter_column(
            "jobs",
            "error",
            type_=sa.String(128),
            existing_type=sa.Text,
            existing_nullable=True,
        )
        op.drop_column("jobs", "payload")
    else:
        with op.batch_alter_table("jobs") as batch:
            batch.alter_column(
                "error",
                type_=sa.String(128),
                existing_type=sa.Text,
                existing_nullable=True,
            )
            batch.drop_column("payload")
