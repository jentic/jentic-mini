"""make agent owner_id nullable

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "n3o4p5q6r7s8"
down_revision: str | None = "m2n3o4p5q6r7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column("agents", "owner_id", existing_type=sa.String(30), nullable=True)
    else:
        with op.batch_alter_table("agents") as batch:
            batch.alter_column("owner_id", existing_type=sa.String(30), nullable=True)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column("agents", "owner_id", existing_type=sa.String(30), nullable=False)
    else:
        with op.batch_alter_table("agents") as batch:
            batch.alter_column("owner_id", existing_type=sa.String(30), nullable=False)
