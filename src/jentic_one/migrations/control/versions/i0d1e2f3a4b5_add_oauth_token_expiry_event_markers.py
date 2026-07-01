"""add oauth token expiry event markers

Revision ID: i0d1e2f3a4b5
Revises: h9c0d1e2f3a4
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i0d1e2f3a4b5"
down_revision: str | None = "h9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Persistent at-most-once dedup markers for the credential-expiry scanner.
    # Nullable: existing tokens start unmarked, so the first sweep that finds
    # them in the warning/expired window emits exactly one event and stamps the
    # corresponding column. No backfill needed.
    op.add_column(
        "oauth_tokens",
        sa.Column("expiring_soon_event_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "oauth_tokens",
        sa.Column("expired_event_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index for the recurring credential-expiry sweep, which filters on
    # revoked_at/expires_at and orders by expires_at. Keeps each ~2-min sweep an
    # index scan over live, expiring tokens rather than a full table scan.
    #
    # Build CONCURRENTLY so we never take an exclusive lock on oauth_tokens.
    # Postgres forbids concurrent index builds inside a transaction, so run it
    # in an autocommit block (commits the column adds above, then runs the
    # CONCURRENTLY DDL outside any transaction).
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_oauth_tokens_expiry_scan",
            "oauth_tokens",
            ["expires_at"],
            postgresql_where=sa.text("revoked_at IS NULL AND expires_at IS NOT NULL"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_oauth_tokens_expiry_scan",
            table_name="oauth_tokens",
            postgresql_concurrently=True,
        )
    op.drop_column("oauth_tokens", "expired_event_at")
    op.drop_column("oauth_tokens", "expiring_soon_event_at")
