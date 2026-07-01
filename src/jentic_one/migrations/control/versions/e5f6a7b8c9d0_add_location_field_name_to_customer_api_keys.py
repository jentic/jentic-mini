"""add location and field_name to customer_api_keys

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_api_keys",
        sa.Column("location", sa.String(20), nullable=False, server_default="header"),
    )
    op.add_column(
        "customer_api_keys",
        sa.Column("field_name", sa.String(255), nullable=False, server_default="Authorization"),
    )


def downgrade() -> None:
    op.drop_column("customer_api_keys", "field_name")
    op.drop_column("customer_api_keys", "location")
