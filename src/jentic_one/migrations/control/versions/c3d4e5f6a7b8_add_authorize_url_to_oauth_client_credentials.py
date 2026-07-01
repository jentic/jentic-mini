"""add authorize_url to oauth_client_credentials

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_client_credentials",
        sa.Column("authorize_url", sa.String(2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oauth_client_credentials", "authorize_url")
