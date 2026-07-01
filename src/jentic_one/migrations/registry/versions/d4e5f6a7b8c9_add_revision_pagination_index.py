"""add revision pagination index

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-11

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import column

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_api_revisions_api_id_created_at_id",
        "api_revisions",
        [column("api_id"), column("created_at").desc(), column("id").desc()],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_revisions_api_id_created_at_id", table_name="api_revisions")
