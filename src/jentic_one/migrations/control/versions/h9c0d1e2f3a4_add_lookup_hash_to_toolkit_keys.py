"""add lookup_hash to toolkit_keys

Revision ID: h9c0d1e2f3a4
Revises: g8b9c0d1e2f3
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h9c0d1e2f3a4"
down_revision: str | None = "g8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SHA-256 digest of the plaintext key, for O(1) broker-side lookup. The
    # salted argon2 ``hashed_key`` stays the verification hash; this is a
    # deterministic lookup index only. Nullable for backfill safety; new keys
    # always populate it.
    op.add_column(
        "toolkit_keys",
        sa.Column("lookup_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_toolkit_keys_lookup_hash",
        "toolkit_keys",
        ["lookup_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_toolkit_keys_lookup_hash", table_name="toolkit_keys")
    op.drop_column("toolkit_keys", "lookup_hash")
