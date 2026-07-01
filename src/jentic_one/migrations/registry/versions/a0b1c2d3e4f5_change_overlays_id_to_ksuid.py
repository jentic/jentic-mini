"""change overlays id to ksuid

Revision ID: a0b1c2d3e4f5
Revises: f6a7b8c9d0e1
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import GUID, json_variant

revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.drop_index("ix_overlays_api_id_created_at_id", table_name="overlays")
    op.drop_index("ix_overlays_api_id", table_name="overlays")
    op.drop_table("overlays")

    op.create_table(
        "overlays",
        sa.Column(
            "id",
            sa.String(length=30),
            server_default=sa.func.generate_ksuid("ovr") if pg else None,
            nullable=False,
        ),
        sa.Column("api_id", GUID(), nullable=False),
        sa.Column("target_revision_id", GUID(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("document", json_variant(), nullable=False),
        sa.Column("contributed_by", sa.String(length=255), nullable=True),
        sa.Column("confirmed_by_execution_id", sa.String(length=255), nullable=True),
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
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["api_id"], ["apis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_overlays_api_id", "overlays", ["api_id"], unique=False)
    op.create_index(
        "ix_overlays_api_id_created_at_id", "overlays", ["api_id", "created_at", "id"], unique=False
    )
    op.create_index("ix_overlays_created_at", "overlays", ["created_at"], unique=False)
    op.create_index("ix_overlays_created_by", "overlays", ["created_by"], unique=False)


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.drop_index("ix_overlays_api_id_created_at_id", table_name="overlays")
    op.drop_index("ix_overlays_api_id", table_name="overlays")
    op.drop_table("overlays")

    op.create_table(
        "overlays",
        sa.Column(
            "id",
            GUID(),
            server_default=sa.text("gen_random_uuid()") if pg else None,
            nullable=False,
        ),
        sa.Column("api_id", GUID(), nullable=False),
        sa.Column("target_revision_id", GUID(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("document", json_variant(), nullable=False),
        sa.Column("contributed_by", sa.String(length=255), nullable=True),
        sa.Column("confirmed_by_execution_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["api_id"], ["apis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_overlays_api_id", "overlays", ["api_id"], unique=False)
    op.create_index(
        "ix_overlays_api_id_created_at_id", "overlays", ["api_id", "created_at", "id"], unique=False
    )
