"""make created_by nullable (temporary)

Temporary migration: relaxes ``created_by`` to nullable on all admin tables
so inserts succeed before the repo/service layers are updated to populate it.
Remove this migration (and re-tighten to NOT NULL) once callers set created_by.

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "q6r7s8t9u0v1"
down_revision: str | None = "p5q6r7s8t9u0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "users",
    "user_secrets",
    "invite_tokens",
    "agents",
    "service_accounts",
    "service_account_credentials",
    "actor_scope_grants",
    "agent_toolkit_bindings",
    "user_permission_grants",
    "access_tokens",
    "refresh_tokens",
    "authorization_codes",
    "external_identities",
    "audit_entries",
    "events",
    "execution_records",
    "jobs",
    "job_results",
)


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    for table in _TABLES:
        if pg:
            op.alter_column(table, "created_by", existing_type=sa.String(255), nullable=True)
        else:
            with op.batch_alter_table(table) as batch:
                batch.alter_column("created_by", existing_type=sa.String(255), nullable=True)
            if table == "users":
                # batch_alter_table cannot preserve expression-based indexes
                op.create_index(
                    "ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True
                )


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    for table in _TABLES:
        if pg:
            op.alter_column(table, "created_by", existing_type=sa.String(255), nullable=False)
        else:
            if table == "users":
                op.drop_index("ix_users_email_lower", table_name="users")
            with op.batch_alter_table(table) as batch:
                batch.alter_column("created_by", existing_type=sa.String(255), nullable=False)
            if table == "users":
                op.create_index(
                    "ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True
                )
