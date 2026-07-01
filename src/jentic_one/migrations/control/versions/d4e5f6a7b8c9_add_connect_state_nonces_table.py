"""add connect_state_nonces table for single-use connect state enforcement

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connect_state_nonces",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("nonce", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "credential_id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_connect_state_nonces_created_at", "connect_state_nonces", ["created_at"])
    op.create_index("ix_connect_state_nonces_created_by", "connect_state_nonces", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_connect_state_nonces_created_by", table_name="connect_state_nonces")
    op.drop_index("ix_connect_state_nonces_created_at", table_name="connect_state_nonces")
    op.drop_table("connect_state_nonces")
