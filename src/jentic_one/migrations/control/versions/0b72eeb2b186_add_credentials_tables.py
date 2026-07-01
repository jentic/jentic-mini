"""add credentials tables

Revision ID: 0b72eeb2b186
Revises:
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import GUID

revision: str = "0b72eeb2b186"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    uuid_default = sa.func.gen_random_uuid() if pg else None

    if pg:
        op.execute("""
            CREATE OR REPLACE FUNCTION generate_ksuid(prefix text) RETURNS text
            LANGUAGE sql VOLATILE
            AS $$
                SELECT prefix || '_' ||
                    lpad(to_hex(extract(epoch FROM clock_timestamp())::bigint), 8, '0') ||
                    substr(replace(gen_random_uuid()::text, '-', ''), 1, 16)
            $$
        """)

    op.create_table(
        "credentials",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("cred") if pg else None,
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("api_vendor", sa.String(100), nullable=False),
        sa.Column("api_name", sa.String(100), nullable=True),
        sa.Column("api_version", sa.String(50), nullable=True),
        sa.Column("active", sa.Boolean, server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credentials_created_by", "credentials", ["created_by"])
    op.create_index("ix_credentials_api_vendor", "credentials", ["api_vendor"])
    op.create_index("ix_credentials_created_at", "credentials", ["created_at"])

    op.create_table(
        "customer_api_keys",
        sa.Column(
            "id",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "credential_id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_api_keys_credential_id", "customer_api_keys", ["credential_id"])
    op.create_index("ix_customer_api_keys_created_at", "customer_api_keys", ["created_at"])
    op.create_index("ix_customer_api_keys_created_by", "customer_api_keys", ["created_by"])

    op.create_table(
        "oauth_client_credentials",
        sa.Column(
            "id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_url", sa.String(2048), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("encrypted_client_secret", sa.Text, nullable=False),
        sa.Column("scope", sa.String(1024), nullable=True),
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
    op.create_index(
        "ix_oauth_client_credentials_created_at", "oauth_client_credentials", ["created_at"]
    )
    op.create_index(
        "ix_oauth_client_credentials_created_by", "oauth_client_credentials", ["created_by"]
    )

    op.create_table(
        "basic_credentials",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column(
            "credential_id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.Text, nullable=False),
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
    op.create_index("ix_basic_credentials_credential_id", "basic_credentials", ["credential_id"])
    op.create_index("ix_basic_credentials_created_at", "basic_credentials", ["created_at"])
    op.create_index("ix_basic_credentials_created_by", "basic_credentials", ["created_by"])

    op.create_table(
        "token_value_credentials",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column(
            "credential_id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("encrypted_token_value", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_token_value_credentials_credential_id", "token_value_credentials", ["credential_id"]
    )
    op.create_index(
        "ix_token_value_credentials_created_at", "token_value_credentials", ["created_at"]
    )
    op.create_index(
        "ix_token_value_credentials_created_by", "token_value_credentials", ["created_by"]
    )

    op.create_table(
        "oauth_tokens",
        sa.Column(
            "id",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "credential_id",
            sa.String(30),
            sa.ForeignKey("credentials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("app_registration_id", sa.String(30), nullable=True),
        sa.Column("platform_application_id", sa.String(30), nullable=True),
        sa.Column("issued_to_user", sa.String(30), nullable=True),
        sa.Column("encrypted_access_token", sa.Text, nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text, nullable=True),
        sa.Column("scope", sa.String(1024), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refreshed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_oauth_tokens_credential_id", "oauth_tokens", ["credential_id"])
    op.create_index("ix_oauth_tokens_app_registration_id", "oauth_tokens", ["app_registration_id"])
    op.create_index(
        "ix_oauth_tokens_platform_application_id", "oauth_tokens", ["platform_application_id"]
    )
    op.create_index("ix_oauth_tokens_created_at", "oauth_tokens", ["created_at"])
    op.create_index("ix_oauth_tokens_created_by", "oauth_tokens", ["created_by"])


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.drop_index("ix_oauth_tokens_created_by", table_name="oauth_tokens")
    op.drop_index("ix_oauth_tokens_created_at", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
    op.drop_index("ix_token_value_credentials_created_by", table_name="token_value_credentials")
    op.drop_index("ix_token_value_credentials_created_at", table_name="token_value_credentials")
    op.drop_table("token_value_credentials")
    op.drop_index("ix_basic_credentials_created_by", table_name="basic_credentials")
    op.drop_index("ix_basic_credentials_created_at", table_name="basic_credentials")
    op.drop_table("basic_credentials")
    op.drop_index("ix_oauth_client_credentials_created_by", table_name="oauth_client_credentials")
    op.drop_index("ix_oauth_client_credentials_created_at", table_name="oauth_client_credentials")
    op.drop_table("oauth_client_credentials")
    op.drop_index("ix_customer_api_keys_created_by", table_name="customer_api_keys")
    op.drop_index("ix_customer_api_keys_created_at", table_name="customer_api_keys")
    op.drop_table("customer_api_keys")
    op.drop_index("ix_credentials_created_at", table_name="credentials")
    op.drop_table("credentials")
    if pg:
        op.execute("DROP FUNCTION IF EXISTS generate_ksuid(text)")
