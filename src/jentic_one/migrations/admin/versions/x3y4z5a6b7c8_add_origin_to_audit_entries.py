"""add origin column to audit_entries

Stores which surface initiated each action (cli, dashboard, api, agent, system)
so operators can filter and trace actions by request origin.

Revision ID: x3y4z5a6b7c8
Revises: w2x3y4z5a6b7
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "x3y4z5a6b7c8"
down_revision: str | None = "w2x3y4z5a6b7"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_entries", sa.Column("origin", sa.String(20), nullable=True))
    op.create_index("ix_audit_entries_origin", "audit_entries", ["origin", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_entries_origin", table_name="audit_entries")
    op.drop_column("audit_entries", "origin")
