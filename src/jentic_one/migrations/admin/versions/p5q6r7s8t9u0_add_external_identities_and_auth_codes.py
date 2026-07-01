"""add external_identities and authorization_codes tables

Revision ID: p5q6r7s8t9u0
Revises: o4p5q6r7s8t9
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p5q6r7s8t9u0"
down_revision: str | None = "o4p5q6r7s8t9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_identities",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("external_subject", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.UniqueConstraint("provider", "external_subject", name="uq_ext_id_provider_subject"),
    )
    op.create_index("ix_ext_id_user_id", "external_identities", ["user_id"])
    op.create_index("ix_external_identities_created_at", "external_identities", ["created_at"])
    op.create_index("ix_external_identities_created_by", "external_identities", ["created_by"])

    op.create_table(
        "authorization_codes",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(30), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=False),
        sa.Column("scopes", sa.String(1024), nullable=False, server_default="openid"),
        sa.Column("nonce", sa.String(255), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_authz_code_hash", "authorization_codes", ["code_hash"], unique=True)
    op.create_index("ix_authorization_codes_created_at", "authorization_codes", ["created_at"])
    op.create_index("ix_authorization_codes_created_by", "authorization_codes", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_authorization_codes_created_by", table_name="authorization_codes")
    op.drop_index("ix_authorization_codes_created_at", table_name="authorization_codes")
    op.drop_index("ix_authz_code_hash", table_name="authorization_codes")
    op.drop_table("authorization_codes")
    op.drop_index("ix_external_identities_created_by", table_name="external_identities")
    op.drop_index("ix_external_identities_created_at", table_name="external_identities")
    op.drop_index("ix_ext_id_user_id", table_name="external_identities")
    op.drop_table("external_identities")
