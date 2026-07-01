"""add provider_configs

Runtime, DB-backed credential provider configuration. The ``config_json``
payload holds the full provider config with secret fields already encrypted;
the table is generic so future configs can migrate to the same pattern.

Revision ID: z5a6b7c8d9e0
Revises: aceeaac9b3f5
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "z5a6b7c8d9e0"
down_revision: str | None = "aceeaac9b3f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    op.create_table(
        "provider_configs",
        sa.Column(
            "id",
            sa.String(30),
            # Postgres generates the ksuid server-side; SQLite has no such
            # function so there is no server_default there. Every insert is
            # expected to go through the ORM model, whose Python-side default
            # (generate_ksuid("pcfg")) supplies the id. A *raw* INSERT on SQLite
            # that omits id would violate NOT NULL — seed/test code must use the
            # ORM model or pass an explicit id.
            server_default=sa.func.generate_ksuid("pcfg") if pg else None,
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
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
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_configs_name", "provider_configs", ["name"], unique=True)
    op.create_index("ix_provider_configs_created_at", "provider_configs", ["created_at"])
    op.create_index("ix_provider_configs_created_by", "provider_configs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_provider_configs_created_by", table_name="provider_configs")
    op.drop_index("ix_provider_configs_created_at", table_name="provider_configs")
    op.drop_index("ix_provider_configs_name", table_name="provider_configs")
    op.drop_table("provider_configs")
