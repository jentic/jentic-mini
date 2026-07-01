"""make created_by nullable (temporary)

Temporary migration: relaxes ``created_by`` to nullable on all registry tables
so inserts succeed before the repo/service layers are updated to populate it.
Remove this migration (and re-tighten to NOT NULL) once callers set created_by.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "apis",
    "api_revisions",
    "spec_files",
    "operations",
    "servers",
    "server_variables",
    "operation_url_indexes",
    "security_schemes",
    "security_scheme_flows",
    "overlays",
)


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    for table in _TABLES:
        if pg:
            op.alter_column(table, "created_by", existing_type=sa.String(255), nullable=True)
        else:
            with op.batch_alter_table(table) as batch:
                batch.alter_column("created_by", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    for table in _TABLES:
        if pg:
            op.alter_column(table, "created_by", existing_type=sa.String(255), nullable=False)
        else:
            with op.batch_alter_table(table) as batch:
                batch.alter_column("created_by", existing_type=sa.String(255), nullable=False)
