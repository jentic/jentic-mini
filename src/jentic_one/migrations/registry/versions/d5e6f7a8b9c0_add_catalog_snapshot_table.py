"""add catalog snapshot table

Revision ID: d5e6f7a8b9c0
Revises: c1d2e3f4a5b6
Create Date: 2026-06-18

The catalog is cached as a single JSON blob (one current snapshot), not a
per-entry table. It is a structurally single-row table: the ``id`` is a fixed
constant (see ``CatalogSnapshot.SINGLETON_ID``), so a refresh upserts that one
row and a concurrent refresh collides on the primary key rather than appending.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import json_variant

revision: str = "d5e6f7a8b9c0"  # pragma: allowlist secret
down_revision: str | None = "c1d2e3f4a5b6"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_snapshots",
        sa.Column(
            "id",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column(
            "entries",
            json_variant(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("catalog_snapshots")
