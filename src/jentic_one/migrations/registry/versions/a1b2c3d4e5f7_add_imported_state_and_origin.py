"""add imported state and origin column

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-06-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_revisions", sa.Column("origin", sa.String(50), nullable=True))
    op.drop_index("ix_api_revisions_one_published", table_name="api_revisions")
    op.create_index(
        "ix_api_revisions_one_active",
        "api_revisions",
        ["api_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('published', 'imported')"),
        sqlite_where=sa.text("state IN ('published', 'imported')"),
    )


def downgrade() -> None:
    op.drop_index("ix_api_revisions_one_active", table_name="api_revisions")
    op.create_index(
        "ix_api_revisions_one_published",
        "api_revisions",
        ["api_id"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
        sqlite_where=sa.text("state = 'published'"),
    )
    op.drop_column("api_revisions", "origin")
