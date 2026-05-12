"""Trusted-proxy forwarded identity: add users.created_via, relax password_hash NOT NULL.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Idempotence: only migrate if created_via is absent.
    cols = {row[1] for row in bind.execute(text("PRAGMA table_info(users)"))}
    if "created_via" in cols:
        return

    # SQLite requires a table-recreate to drop the NOT NULL constraint on
    # password_hash; batch_alter_table handles this transparently.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("created_via", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    cols = {row[1] for row in bind.execute(text("PRAGMA table_info(users)"))}
    if "created_via" not in cols:
        return

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("created_via")
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=False,
        )
