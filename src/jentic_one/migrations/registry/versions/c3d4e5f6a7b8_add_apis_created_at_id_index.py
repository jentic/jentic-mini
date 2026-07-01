"""add apis created_at id index

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-10

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_apis_created_at_id",
        "apis",
        ["created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_apis_created_at_id", table_name="apis")
