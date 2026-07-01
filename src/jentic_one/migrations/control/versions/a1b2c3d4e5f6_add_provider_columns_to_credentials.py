"""add provider columns to credentials

Revision ID: a1b2c3d4e5f6
Revises: 3f1c9a2d4e87
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "3f1c9a2d4e87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "credentials",
        sa.Column("provider", sa.String(50), nullable=False, server_default=sa.text("'static'")),
    )
    op.add_column(
        "credentials",
        sa.Column("provider_account_ref", sa.String(255), nullable=True),
    )
    op.create_index("ix_credentials_provider", "credentials", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_credentials_provider", table_name="credentials")
    op.drop_column("credentials", "provider_account_ref")
    op.drop_column("credentials", "provider")
