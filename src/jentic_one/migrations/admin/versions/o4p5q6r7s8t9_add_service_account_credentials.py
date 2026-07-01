"""add service_account_credentials table

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "o4p5q6r7s8t9"
down_revision: str | None = "n3o4p5q6r7s8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_account_credentials",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column(
            "service_account_id",
            sa.String(30),
            sa.ForeignKey("service_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_secret_hash", sa.String(128), nullable=True),
        sa.Column("api_key_hash", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_sa_credentials_service_account_id",
        "service_account_credentials",
        ["service_account_id"],
        unique=True,
    )
    op.create_index(
        "ix_service_account_credentials_created_at",
        "service_account_credentials",
        ["created_at"],
    )
    op.create_index(
        "ix_service_account_credentials_created_by",
        "service_account_credentials",
        ["created_by"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_account_credentials_created_by", table_name="service_account_credentials"
    )
    op.drop_index(
        "ix_service_account_credentials_created_at", table_name="service_account_credentials"
    )
    op.drop_index("ix_sa_credentials_service_account_id", table_name="service_account_credentials")
    op.drop_table("service_account_credentials")
