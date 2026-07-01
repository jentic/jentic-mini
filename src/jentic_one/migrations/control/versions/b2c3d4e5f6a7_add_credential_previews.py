"""add credential preview columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_api_keys",
        sa.Column("key_preview", sa.String(16), nullable=True),
    )
    op.add_column(
        "token_value_credentials",
        sa.Column("token_preview", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("token_value_credentials", "token_preview")
    op.drop_column("customer_api_keys", "key_preview")
