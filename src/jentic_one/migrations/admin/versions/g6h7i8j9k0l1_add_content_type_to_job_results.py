"""add content_type to job_results

Revision ID: g6h7i8j9k0l1
Revises: a6b7c8d9e0f1
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g6h7i8j9k0l1"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_results", sa.Column("content_type", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("job_results", "content_type")
