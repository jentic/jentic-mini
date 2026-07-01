"""add token tables

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-06-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "l1m2n3o4p5q6"
down_revision: str | None = "k0l1m2n3o4p5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    op.create_table(
        "access_tokens",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("at") if pg else None,
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("token_family_id", sa.String(30), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_tokens_token_hash", "access_tokens", ["token_hash"], unique=True)
    op.create_index("ix_access_tokens_actor_id", "access_tokens", ["actor_id"])
    op.create_index("ix_access_tokens_token_family_id", "access_tokens", ["token_family_id"])
    op.create_index("ix_access_tokens_expires_at", "access_tokens", ["expires_at"])
    op.create_index("ix_access_tokens_created_at", "access_tokens", ["created_at"])
    op.create_index("ix_access_tokens_created_by", "access_tokens", ["created_by"])

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("rt") if pg else None,
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("token_family_id", sa.String(30), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.String(30), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_actor_id", "refresh_tokens", ["actor_id"])
    op.create_index("ix_refresh_tokens_token_family_id", "refresh_tokens", ["token_family_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_tokens_created_at", "refresh_tokens", ["created_at"])
    op.create_index("ix_refresh_tokens_created_by", "refresh_tokens", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_created_by", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_created_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_access_tokens_created_by", table_name="access_tokens")
    op.drop_index("ix_access_tokens_created_at", table_name="access_tokens")
    op.drop_table("access_tokens")
