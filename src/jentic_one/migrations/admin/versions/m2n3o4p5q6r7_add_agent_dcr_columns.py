"""add agent dcr columns

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m2n3o4p5q6r7"
down_revision: str | None = "l1m2n3o4p5q6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("jwks", sa.JSON(), nullable=True))
    op.add_column(
        "agents", sa.Column("registration_access_token_hash", sa.String(64), nullable=True)
    )
    op.add_column("agents", sa.Column("rat_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_agents_registration_access_token_hash",
        "agents",
        ["registration_access_token_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_agents_registration_access_token_hash", table_name="agents")
    op.drop_column("agents", "rat_expires_at")
    op.drop_column("agents", "registration_access_token_hash")
    op.drop_column("agents", "jwks")
