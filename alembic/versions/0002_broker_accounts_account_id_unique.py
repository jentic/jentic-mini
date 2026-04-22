"""Add account_id to oauth_broker_accounts unique constraint and primary key

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-02
"""

from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Recreate oauth_broker_accounts with account_id included in the unique
    # constraint and the row id. The old UNIQUE(broker_id, external_user_id, api_host)
    # allowed only one account per api_host per user, which broke multiple Gmail accounts.
    op.execute("ALTER TABLE oauth_broker_accounts RENAME TO oauth_broker_accounts_old")

    op.execute("""
    CREATE TABLE oauth_broker_accounts (
        id               TEXT PRIMARY KEY,
        broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        external_user_id TEXT NOT NULL,
        api_host         TEXT NOT NULL,
        app_slug         TEXT NOT NULL,
        account_id       TEXT NOT NULL,
        label            TEXT,
        healthy          INTEGER DEFAULT 1,
        synced_at        REAL DEFAULT (unixepoch()),
        api_id           TEXT,
        UNIQUE(broker_id, external_user_id, api_host, account_id)
    )
    """)

    # Migrate existing rows — rebuild the id to include account_id
    op.execute("""
    INSERT INTO oauth_broker_accounts
        (id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at, api_id)
    SELECT
        broker_id || ':' || external_user_id || ':' || api_host || ':' || account_id,
        broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at, api_id
    FROM oauth_broker_accounts_old
    """)

    op.execute("DROP TABLE oauth_broker_accounts_old")


def downgrade():
    op.execute("ALTER TABLE oauth_broker_accounts RENAME TO oauth_broker_accounts_new")

    op.execute("""
    CREATE TABLE oauth_broker_accounts (
        id               TEXT PRIMARY KEY,
        broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        external_user_id TEXT NOT NULL,
        api_host         TEXT NOT NULL,
        app_slug         TEXT NOT NULL,
        account_id       TEXT NOT NULL,
        label            TEXT,
        healthy          INTEGER DEFAULT 1,
        synced_at        REAL DEFAULT (unixepoch()),
        api_id           TEXT,
        UNIQUE(broker_id, external_user_id, api_host)
    )
    """)

    op.execute("""
    INSERT OR IGNORE INTO oauth_broker_accounts
        (id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at, api_id)
    SELECT
        broker_id || ':' || external_user_id || ':' || api_host,
        broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at, api_id
    FROM oauth_broker_accounts_new
    """)

    op.execute("DROP TABLE oauth_broker_accounts_new")
