"""add toolkit tables

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    op.create_table(
        "toolkits",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("tk") if pg else None,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column(
            "permissions",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            server_default=sa.text("'[]'"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_toolkits_name"),
    )
    op.create_index("ix_toolkits_created_at", "toolkits", ["created_at"])
    op.create_index("ix_toolkits_created_by", "toolkits", ["created_by"])

    op.create_table(
        "toolkit_keys",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("ck") if pg else None,
            nullable=False,
        ),
        sa.Column("toolkit_id", sa.String(30), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column(
            "allowed_ips",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("revoked", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("key_preview", sa.String(50), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
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
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["toolkit_id"], ["toolkits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_toolkit_keys_toolkit_id", "toolkit_keys", ["toolkit_id"])
    op.create_index("ix_toolkit_keys_created_at", "toolkit_keys", ["created_at"])
    op.create_index("ix_toolkit_keys_created_by", "toolkit_keys", ["created_by"])

    op.create_table(
        "toolkit_credential_bindings",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("tcb") if pg else None,
            nullable=False,
        ),
        sa.Column("toolkit_id", sa.String(30), nullable=False),
        sa.Column("credential_id", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "bound_at",
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
        sa.ForeignKeyConstraint(["toolkit_id"], ["toolkits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("toolkit_id", "credential_id", name="uq_toolkit_credential_binding"),
    )
    op.create_index(
        "ix_toolkit_credential_bindings_created_at",
        "toolkit_credential_bindings",
        ["created_at"],
    )
    op.create_index(
        "ix_toolkit_credential_bindings_created_by",
        "toolkit_credential_bindings",
        ["created_by"],
    )

    op.create_table(
        "toolkit_permission_rules",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("tpr") if pg else None,
            nullable=False,
        ),
        sa.Column("toolkit_id", sa.String(30), nullable=False),
        sa.Column("credential_id", sa.String(30), nullable=False),
        sa.Column("effect", sa.String(10), nullable=False),
        sa.Column(
            "methods",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("path", sa.String(1000), nullable=True),
        sa.Column(
            "operations",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("is_system", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column("sequence", sa.Integer, nullable=False),
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
        sa.ForeignKeyConstraint(["toolkit_id"], ["toolkits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_toolkit_permission_rules_binding_seq",
        "toolkit_permission_rules",
        ["toolkit_id", "credential_id", "sequence"],
    )
    op.create_index(
        "ix_toolkit_permission_rules_created_at",
        "toolkit_permission_rules",
        ["created_at"],
    )
    op.create_index(
        "ix_toolkit_permission_rules_created_by",
        "toolkit_permission_rules",
        ["created_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_toolkit_permission_rules_created_by", table_name="toolkit_permission_rules")
    op.drop_index("ix_toolkit_permission_rules_created_at", table_name="toolkit_permission_rules")
    op.drop_index("ix_toolkit_permission_rules_binding_seq", "toolkit_permission_rules")
    op.drop_table("toolkit_permission_rules")
    op.drop_index(
        "ix_toolkit_credential_bindings_created_by", table_name="toolkit_credential_bindings"
    )
    op.drop_index(
        "ix_toolkit_credential_bindings_created_at", table_name="toolkit_credential_bindings"
    )
    op.drop_table("toolkit_credential_bindings")
    op.drop_index("ix_toolkit_keys_created_by", table_name="toolkit_keys")
    op.drop_index("ix_toolkit_keys_created_at", table_name="toolkit_keys")
    op.drop_index("ix_toolkit_keys_toolkit_id", "toolkit_keys")
    op.drop_table("toolkit_keys")
    op.drop_index("ix_toolkits_created_by", table_name="toolkits")
    op.drop_index("ix_toolkits_created_at", table_name="toolkits")
    op.drop_table("toolkits")
