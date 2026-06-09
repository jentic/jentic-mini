"""Add server_variables column to oauth_broker_connect_labels.

Multi-tenant public specs (e.g. Jira's https://{your-domain}.atlassian.net)
carry an OpenAPI server template variable that must be bound to a concrete
tenant value (e.g. your-domain=acme) to reach the right host. For the
Pipedream OAuth path the tenant is collected at connect-link time and carried
through the connect-callback into oauth_broker_connect_labels, so that
discover_accounts can (a) resolve the real host for the credential route and
(b) persist server_variables on the resulting pipedream_oauth credential.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def upgrade() -> None:
    # JSON-encoded dict of OpenAPI server variables (e.g. {"your-domain": "acme"}).
    if not _has_column("oauth_broker_connect_labels", "server_variables"):
        op.execute("ALTER TABLE oauth_broker_connect_labels ADD COLUMN server_variables TEXT")


def downgrade() -> None:
    # SQLite cannot drop a column directly; recreate the table without it.
    op.execute("PRAGMA foreign_keys = OFF")
    op.execute("DROP TABLE IF EXISTS oauth_broker_connect_labels_old")
    op.execute("""
    CREATE TABLE oauth_broker_connect_labels_old (
        id               TEXT PRIMARY KEY,
        broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        external_user_id TEXT NOT NULL,
        app_slug         TEXT NOT NULL,
        label            TEXT NOT NULL,
        api_id           TEXT,
        created_at       REAL DEFAULT (unixepoch())
    )
    """)
    op.execute("""
    INSERT OR IGNORE INTO oauth_broker_connect_labels_old
        SELECT id, broker_id, external_user_id, app_slug, label, api_id, created_at
        FROM oauth_broker_connect_labels
    """)
    op.execute("DROP TABLE oauth_broker_connect_labels")
    op.execute("ALTER TABLE oauth_broker_connect_labels_old RENAME TO oauth_broker_connect_labels")
    op.execute("PRAGMA foreign_keys = ON")
