"""add user permission grants

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "user_permission_grants",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("perm") if pg else None,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("granted_by", sa.String(30), nullable=True),
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
        sa.UniqueConstraint("user_id", "permission", name="uq_user_permission_grants_user_perm"),
    )
    op.create_index(
        "ix_user_permission_grants_permission", "user_permission_grants", ["permission"]
    )
    op.create_index(
        "ix_user_permission_grants_created_at", "user_permission_grants", ["created_at"]
    )
    op.create_index(
        "ix_user_permission_grants_created_by", "user_permission_grants", ["created_by"]
    )

    # No bootstrap grant seed: the first admin's `org:admin` grant is created at
    # runtime by `AuthService.bootstrap_admin` during first-run setup.


def downgrade() -> None:
    op.drop_index("ix_user_permission_grants_created_by", table_name="user_permission_grants")
    op.drop_index("ix_user_permission_grants_created_at", table_name="user_permission_grants")
    op.drop_table("user_permission_grants")
