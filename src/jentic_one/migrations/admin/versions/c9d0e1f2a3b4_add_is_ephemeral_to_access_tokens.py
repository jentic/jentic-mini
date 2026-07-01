"""add is_ephemeral column to access_tokens

Encodes an access token's lifecycle explicitly so token resolution can decide
whether to resolve scopes live from actor_scope_grants (long-lived pairs) or
keep the frozen downscoped snapshot (ephemeral mint tokens) without probing the
refresh_tokens table.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"  # pragma: allowlist secret
down_revision: str | None = "b8c9d0e1f2a3"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "access_tokens",
        sa.Column(
            "is_ephemeral",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("access_tokens", "is_ephemeral")
