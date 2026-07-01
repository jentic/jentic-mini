"""add agent_credentials table

Stores hashed API keys and client secrets for agent authentication,
mirroring service_account_credentials.

Revision ID: 24852503fc19
Revises: v1w2x3y4z5a6
Create Date: 2026-06-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "24852503fc19"
down_revision: str | None = "v1w2x3y4z5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_credentials",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(30),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_secret_hash", sa.String(128), nullable=True),
        sa.Column("api_key_hash", sa.String(128), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(30), nullable=True),
    )
    op.create_index("ix_agent_credentials_agent_id", "agent_credentials", ["agent_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agent_credentials_agent_id", table_name="agent_credentials")
    op.drop_table("agent_credentials")
