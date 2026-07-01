"""add users secrets invites

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("usr") if pg else None,
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("auth_provider", sa.String(16), server_default="local", nullable=False),
        sa.Column("external_subject_id", sa.String(255), nullable=True),
        sa.Column("must_change_password", sa.Boolean, server_default="false", nullable=False),
        sa.Column("invite_state", sa.String(16), server_default="pending", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
    op.create_index("ix_users_invite_state", "users", ["invite_state"])
    op.create_index("ix_users_active", "users", ["active"])
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_created_by", "users", ["created_by"])

    op.create_table(
        "user_secrets",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("usec") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("password_algo", sa.String(32), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_secrets_created_at", "user_secrets", ["created_at"])
    op.create_index("ix_user_secrets_created_by", "user_secrets", ["created_by"])

    op.create_table(
        "invite_tokens",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("inv") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invite_tokens_user_id", "invite_tokens", ["user_id"])
    op.create_index("ix_invite_tokens_token_hash", "invite_tokens", ["token_hash"], unique=True)
    op.create_index(
        "ix_invite_tokens_expires_at",
        "invite_tokens",
        ["expires_at"],
        postgresql_where=sa.text("redeemed_at IS NULL"),
        sqlite_where=sa.text("redeemed_at IS NULL"),
    )
    op.create_index("ix_invite_tokens_created_at", "invite_tokens", ["created_at"])
    op.create_index("ix_invite_tokens_created_by", "invite_tokens", ["created_by"])

    # No bootstrap admin seed: the first admin is created at runtime via the
    # one-time `POST /users:create-admin` endpoint (or `jenticctl setup`), so the
    # database ships with zero users and no default credentials.


def downgrade() -> None:
    op.drop_index("ix_invite_tokens_created_by", table_name="invite_tokens")
    op.drop_index("ix_invite_tokens_created_at", table_name="invite_tokens")
    op.drop_table("invite_tokens")
    op.drop_index("ix_user_secrets_created_by", table_name="user_secrets")
    op.drop_index("ix_user_secrets_created_at", table_name="user_secrets")
    op.drop_table("user_secrets")
    op.drop_index("ix_users_created_by", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
