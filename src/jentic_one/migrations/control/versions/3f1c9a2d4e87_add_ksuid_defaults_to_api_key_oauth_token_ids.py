"""add ksuid server defaults to customer_api_keys.id and oauth_tokens.id

Revision ID: 3f1c9a2d4e87
Revises: 0b72eeb2b186
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f1c9a2d4e87"  # pragma: allowlist secret
down_revision: str | None = "0b72eeb2b186"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        # KSUID ids are generated app-side on SQLite; no server default to set.
        return
    op.alter_column(
        "customer_api_keys",
        "id",
        server_default=sa.func.generate_ksuid("cak"),
    )
    op.alter_column(
        "oauth_tokens",
        "id",
        server_default=sa.func.generate_ksuid("oat"),
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column("oauth_tokens", "id", server_default=None)
    op.alter_column("customer_api_keys", "id", server_default=None)
