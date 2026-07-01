"""add revisions source_url state index

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-06-20

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_api_revisions_source_url_state",
        "api_revisions",
        ["source_url", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_revisions_source_url_state", table_name="api_revisions")
