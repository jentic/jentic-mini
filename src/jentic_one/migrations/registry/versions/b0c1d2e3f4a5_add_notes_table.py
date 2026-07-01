"""add notes table

Revision ID: b0c1d2e3f4a5
Revises: a0b1c2d3e4f5
Create Date: 2026-06-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import GUID

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "notes",
        sa.Column(
            "id",
            sa.String(length=30),
            server_default=sa.text("generate_ksuid('note')") if pg else None,
            nullable=False,
        ),
        sa.Column("resource_api_id", GUID(), nullable=True),
        sa.Column("resource_operation_id", sa.String(length=255), nullable=True),
        sa.Column("resource_execution_id", sa.String(length=255), nullable=True),
        sa.Column("resource_credential_id", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=True),
        sa.Column(
            "confidence_source",
            sa.String(length=20),
            server_default=sa.text("'client'"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("related_execution_id", sa.String(length=255), nullable=True),
        sa.Column("revision", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.ForeignKeyConstraint(["resource_api_id"], ["apis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_created_at_id", "notes", ["created_at", "id"], unique=False)
    op.create_index("ix_notes_created_at", "notes", ["created_at"], unique=False)
    op.create_index("ix_notes_resource_api_id", "notes", ["resource_api_id"], unique=False)
    op.create_index(
        "ix_notes_resource_operation_id", "notes", ["resource_operation_id"], unique=False
    )
    op.create_index(
        "ix_notes_resource_execution_id", "notes", ["resource_execution_id"], unique=False
    )
    op.create_index(
        "ix_notes_resource_credential_id", "notes", ["resource_credential_id"], unique=False
    )
    op.create_index("ix_notes_created_by", "notes", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notes_created_by", table_name="notes")
    op.drop_index("ix_notes_created_at", table_name="notes")
    op.drop_index("ix_notes_resource_credential_id", table_name="notes")
    op.drop_index("ix_notes_resource_execution_id", table_name="notes")
    op.drop_index("ix_notes_resource_operation_id", table_name="notes")
    op.drop_index("ix_notes_resource_api_id", table_name="notes")
    op.drop_index("ix_notes_created_at_id", table_name="notes")
    op.drop_table("notes")
