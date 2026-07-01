"""add api_host to execution_records

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i8j9k0l1m2n3"
down_revision: str | None = "h7i8j9k0l1m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_records", sa.Column("api_host", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("execution_records", "api_host")
