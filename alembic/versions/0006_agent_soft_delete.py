"""Add agents.deleted_at for soft deregister (read-only archive).

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-30
"""

from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agents ADD COLUMN deleted_at REAL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_deleted_at ON agents(deleted_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_agents_deleted_at")
    # SQLite: column left in place (no DROP COLUMN in baseline tooling)
