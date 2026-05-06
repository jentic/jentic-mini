"""Agent identity: OAuth DCR, opaque tokens, toolkit grants, soft deregister.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-30
"""

from alembic import op
from sqlalchemy import text


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            client_id                  TEXT PRIMARY KEY,
            client_name                TEXT NOT NULL,
            status                     TEXT NOT NULL DEFAULT 'pending',
            jwks_json                  TEXT NOT NULL,
            registration_token_hash    TEXT,
            registration_token_expires_at REAL,
            registration_client_uri    TEXT,
            created_at                 REAL DEFAULT (unixepoch()),
            approved_at                REAL,
            approved_by                TEXT,
            denied_at                  REAL,
            disabled_at                REAL,
            deleted_at                 REAL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_deleted_at ON agents(deleted_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_toolkit_grants (
            client_id   TEXT NOT NULL REFERENCES agents(client_id) ON DELETE CASCADE,
            toolkit_id  TEXT NOT NULL REFERENCES toolkits(id) ON DELETE CASCADE,
            granted_at  REAL DEFAULT (unixepoch()),
            granted_by  TEXT,
            PRIMARY KEY (client_id, toolkit_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_tokens (
            token_hash        TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL REFERENCES agents(client_id) ON DELETE CASCADE,
            token_type        TEXT NOT NULL,
            expires_at        REAL NOT NULL,
            consumed_at       REAL,
            parent_token_hash TEXT,
            created_at        REAL DEFAULT (unixepoch())
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_tokens_client ON agent_tokens(client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_tokens_expires ON agent_tokens(expires_at)")
    # Refresh-token rotation defence-in-depth: at most one live child per parent
    # so a racing reuse can't successfully mint a duplicate. Partial because root
    # tokens (parent IS NULL) and revoked siblings should not collide.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_tokens_parent_type "
        "ON agent_tokens(parent_token_hash, token_type) "
        "WHERE parent_token_hash IS NOT NULL"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_nonces (
            jti         TEXT PRIMARY KEY,
            client_id   TEXT NOT NULL REFERENCES agents(client_id) ON DELETE CASCADE,
            expires_at  REAL NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_nonces_expires ON agent_nonces(expires_at)")

    # SQLite has no `ALTER TABLE … ADD COLUMN IF NOT EXISTS`; introspect via
    # PRAGMA so genuine errors still raise instead of being swallowed.
    bind = op.get_bind()
    cols = {row[1] for row in bind.execute(text("PRAGMA table_info(executions)"))}
    if "agent_id" not in cols:
        op.execute("ALTER TABLE executions ADD COLUMN agent_id TEXT DEFAULT NULL")
    # Trace tenant scoping: non-admin reads filter by agent_id; partial index
    # keeps it cheap given most pre-feature rows have NULL.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_agent_created "
        "ON executions(agent_id, created_at) "
        "WHERE agent_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_nonces")
    op.execute("DROP TABLE IF EXISTS agent_tokens")
    op.execute("DROP TABLE IF EXISTS agent_toolkit_grants")
    op.execute("DROP TABLE IF EXISTS agents")
    # SQLite cannot DROP COLUMN easily — leave executions.agent_id on downgrade
