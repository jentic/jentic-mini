"""add ix_agent_toolkit_bindings_toolkit_id

Adds a B-tree index on ``toolkit_id`` in the agent_toolkit_bindings table to
support efficient reverse lookups (agents bound to a given toolkit).

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
Create Date: 2026-06-22

"""

from collections.abc import Sequence

from alembic import op

revision: str = "s8t9u0v1w2x3"
down_revision: str | None = "r7s8t9u0v1w2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_agent_toolkit_bindings_toolkit_id",
        "agent_toolkit_bindings",
        ["toolkit_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_toolkit_bindings_toolkit_id", table_name="agent_toolkit_bindings")
