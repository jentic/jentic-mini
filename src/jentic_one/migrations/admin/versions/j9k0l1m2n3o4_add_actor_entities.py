"""add actor entities

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "j9k0l1m2n3o4"
down_revision: str | None = "i8j9k0l1m2n3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "agents",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("agnt") if pg else None,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("registered_by", sa.String(30), nullable=False),
        sa.Column(
            "parent_agent_id",
            sa.String(30),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("denial_reason", sa.String(1024), nullable=True),
        sa.Column("denied_by", sa.String(30), nullable=True),
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
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_created_at", "agents", ["created_at"])
    op.create_index("ix_agents_created_by", "agents", ["created_by"])

    op.create_table(
        "service_accounts",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("sva") if pg else None,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("registered_by", sa.String(30), nullable=False),
        sa.Column(
            "approved_by",
            sa.String(30),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("denial_reason", sa.String(1024), nullable=True),
        sa.Column("denied_by", sa.String(30), nullable=True),
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
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_accounts_owner_id", "service_accounts", ["owner_id"])
    op.create_index("ix_service_accounts_status", "service_accounts", ["status"])
    op.create_index("ix_service_accounts_created_at", "service_accounts", ["created_at"])
    op.create_index("ix_service_accounts_created_by", "service_accounts", ["created_by"])

    op.create_table(
        "actor_scope_grants",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("asg") if pg else None,
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
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
        sa.UniqueConstraint("actor_id", "scope", name="uq_actor_scope_grants_actor_scope"),
    )
    op.create_index("ix_actor_scope_grants_scope", "actor_scope_grants", ["scope"])
    op.create_index("ix_actor_scope_grants_actor", "actor_scope_grants", ["actor_id", "actor_type"])
    op.create_index("ix_actor_scope_grants_created_at", "actor_scope_grants", ["created_at"])
    op.create_index("ix_actor_scope_grants_created_by", "actor_scope_grants", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_actor_scope_grants_created_by", table_name="actor_scope_grants")
    op.drop_index("ix_actor_scope_grants_created_at", table_name="actor_scope_grants")
    op.drop_table("actor_scope_grants")
    op.drop_index("ix_service_accounts_created_by", table_name="service_accounts")
    op.drop_index("ix_service_accounts_created_at", table_name="service_accounts")
    op.drop_table("service_accounts")
    op.drop_index("ix_agents_created_by", table_name="agents")
    op.drop_index("ix_agents_created_at", table_name="agents")
    op.drop_table("agents")
