"""Drop UNIQUE(broker_id, external_user_id, app_slug) from oauth_broker_connect_labels.

Previously the table had a single slot per app_slug, so connecting two accounts of
the same app (e.g. two Gmail accounts) before either sync completed would silently
overwrite the first pending label with the second. The primary key (UUID) already
uniquely identifies each row; the slug-level UNIQUE was an overly strict guard
that created a label-clobbering race.

SQLite does not support DROP CONSTRAINT, so we recreate the table without it.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate table without the UNIQUE(broker_id, external_user_id, app_slug) constraint.
    # Rows are already uniquely identified by the UUID primary key.
    # Drop any leftover _new table from a partial previous run (e.g. interrupted by WatchFiles reload).
    op.execute("PRAGMA foreign_keys = OFF")
    op.execute("DROP TABLE IF EXISTS oauth_broker_connect_labels_new")
    op.execute("""
    CREATE TABLE oauth_broker_connect_labels_new (
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
    INSERT OR IGNORE INTO oauth_broker_connect_labels_new
        SELECT id, broker_id, external_user_id, app_slug, label, api_id, created_at
        FROM oauth_broker_connect_labels
    """)
    op.execute("DROP TABLE oauth_broker_connect_labels")
    op.execute("ALTER TABLE oauth_broker_connect_labels_new RENAME TO oauth_broker_connect_labels")
    op.execute("PRAGMA foreign_keys = ON")


def downgrade() -> None:
    # Restore the UNIQUE constraint (best-effort — duplicate rows dropped arbitrarily).
    op.execute("""
    CREATE TABLE IF NOT EXISTS oauth_broker_connect_labels_old (
        id               TEXT PRIMARY KEY,
        broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        external_user_id TEXT NOT NULL,
        app_slug         TEXT NOT NULL,
        label            TEXT NOT NULL,
        api_id           TEXT,
        created_at       REAL DEFAULT (unixepoch()),
        UNIQUE(broker_id, external_user_id, app_slug)
    )
    """)
    op.execute("""
    INSERT OR IGNORE INTO oauth_broker_connect_labels_old
        SELECT id, broker_id, external_user_id, app_slug, label, api_id, created_at
        FROM oauth_broker_connect_labels
    """)
    op.execute("DROP TABLE oauth_broker_connect_labels")
    op.execute("ALTER TABLE oauth_broker_connect_labels_old RENAME TO oauth_broker_connect_labels")
