"""Baseline schema — all tables in final form.

Revision ID: 0001
Revises: None
Create Date: 2026-03-27

This is the initial schema for Jentic Mini, consolidating all tables
that were previously created inline in src/db.py. All columns are in
their final form — no ALTER TABLE migrations needed.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and seed default data."""

    # ── Core API Registry ────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS apis (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        spec_path   TEXT,
        base_url    TEXT,
        created_at  REAL DEFAULT (unixepoch())
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS operations (
        id           TEXT PRIMARY KEY,
        api_id       TEXT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
        operation_id TEXT,
        jentic_id    TEXT UNIQUE,
        method       TEXT,
        path         TEXT,
        summary      TEXT,
        description  TEXT
    )
    """)

    # ── Credential Vault ─────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS credentials (
        id              TEXT PRIMARY KEY,
        label           TEXT NOT NULL,
        env_var         TEXT UNIQUE,
        encrypted_value TEXT NOT NULL,
        created_at      REAL DEFAULT (unixepoch()),
        updated_at      REAL,
        api_id          TEXT,
        auth_type       TEXT,
        identity        TEXT
    )
    """)

    # ── Toolkits ─────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS toolkits (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        api_key     TEXT NOT NULL UNIQUE,
        simulate    INTEGER NOT NULL DEFAULT 0,
        disabled    INTEGER NOT NULL DEFAULT 0,
        created_at  REAL DEFAULT (unixepoch()),
        updated_at  REAL DEFAULT (unixepoch())
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS toolkit_credentials (
        id            TEXT PRIMARY KEY,
        toolkit_id    TEXT NOT NULL REFERENCES toolkits(id) ON DELETE CASCADE,
        credential_id TEXT NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
        alias         TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        UNIQUE (toolkit_id, credential_id)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS toolkit_keys (
        id          TEXT PRIMARY KEY,
        toolkit_id  TEXT NOT NULL REFERENCES toolkits(id) ON DELETE CASCADE,
        api_key     TEXT NOT NULL UNIQUE,
        label       TEXT,
        allowed_ips TEXT,
        created_at  REAL DEFAULT (unixepoch()),
        revoked_at  REAL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS toolkit_policies (
        id             TEXT PRIMARY KEY,
        toolkit_id     TEXT NOT NULL UNIQUE REFERENCES toolkits(id) ON DELETE CASCADE,
        default_action TEXT NOT NULL DEFAULT 'allow',
        rules          TEXT NOT NULL DEFAULT '[]',
        summary        TEXT,
        created_at     REAL DEFAULT (unixepoch()),
        updated_at     REAL DEFAULT (unixepoch())
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS credential_policies (
        id            TEXT PRIMARY KEY,
        credential_id TEXT NOT NULL UNIQUE REFERENCES credentials(id) ON DELETE CASCADE,
        rules         TEXT NOT NULL DEFAULT '[]',
        summary       TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        updated_at    REAL DEFAULT (unixepoch())
    )
    """)

    # ── API Keys ─────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id          TEXT PRIMARY KEY,
        api_key     TEXT NOT NULL UNIQUE,
        label       TEXT NOT NULL,
        scopes      TEXT NOT NULL DEFAULT '["execute"]',
        owner_type  TEXT NOT NULL DEFAULT 'agent',
        created_at  REAL DEFAULT (unixepoch()),
        last_used   REAL
    )
    """)

    # ── Permission Requests ──────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS permission_requests (
        id            TEXT PRIMARY KEY,
        toolkit_id    TEXT REFERENCES toolkits(id) ON DELETE CASCADE,
        api_key_id    TEXT,
        type          TEXT NOT NULL,
        payload       TEXT NOT NULL DEFAULT '{}',
        reason        TEXT,
        status        TEXT NOT NULL DEFAULT 'pending',
        user_url      TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        resolved_at   REAL
    )
    """)

    # ── Execution Traces ─────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS executions (
        id             TEXT PRIMARY KEY,
        toolkit_id     TEXT,
        api_key_id     TEXT,
        operation_id   TEXT,
        workflow_id    TEXT,
        spec_path      TEXT,
        inputs_hash    TEXT,
        status         TEXT NOT NULL DEFAULT 'running',
        http_status    INTEGER,
        duration_ms    INTEGER,
        error          TEXT,
        created_at     REAL DEFAULT (unixepoch()),
        completed_at   REAL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS execution_steps (
        id           TEXT PRIMARY KEY,
        execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
        step_id      TEXT NOT NULL,
        operation    TEXT,
        status       TEXT,
        http_status  INTEGER,
        inputs       TEXT,
        output       TEXT,
        error        TEXT,
        started_at   REAL DEFAULT (unixepoch()),
        completed_at REAL
    )
    """)

    # ── Notes ────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id           TEXT PRIMARY KEY,
        resource     TEXT NOT NULL,
        type         TEXT,
        note         TEXT NOT NULL,
        execution_id TEXT,
        confidence   TEXT,
        source       TEXT,
        created_at   REAL DEFAULT (unixepoch())
    )
    """)

    # ── Auth Override Log ────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS auth_override_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id       TEXT,
        operation_id TEXT,
        workflow_id  TEXT,
        header_names TEXT NOT NULL,
        success      INTEGER NOT NULL DEFAULT 0,
        created_at   REAL DEFAULT (unixepoch())
    )
    """)

    # ── Workflows ────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        slug         TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        description  TEXT,
        arazzo_path  TEXT NOT NULL,
        input_schema TEXT,
        steps_count  INTEGER DEFAULT 0,
        involved_apis TEXT,
        created_at   REAL DEFAULT (unixepoch())
    )
    """)

    # ── Jobs ─────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id              TEXT PRIMARY KEY,
        kind            TEXT NOT NULL DEFAULT 'workflow',
        slug_or_id      TEXT NOT NULL,
        toolkit_id      TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',
        result          TEXT,
        error           TEXT,
        http_status     INTEGER,
        upstream_async  INTEGER NOT NULL DEFAULT 0,
        upstream_job_url TEXT,
        trace_id        TEXT,
        inputs          TEXT,
        callback_url    TEXT,
        created_at      REAL DEFAULT (unixepoch()),
        completed_at    REAL
    )
    """)

    # ── Users & Settings ─────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            TEXT PRIMARY KEY,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at    REAL DEFAULT (unixepoch())
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # ── API Overlays ─────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS api_overlays (
        id              TEXT PRIMARY KEY,
        api_id          TEXT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
        overlay         TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'pending',
        contributed_by  TEXT,
        confirmed_at    REAL,
        confirmed_by_execution TEXT,
        created_at      REAL DEFAULT (unixepoch())
    )
    """)

    # ── OAuth Brokers ────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS oauth_brokers (
        id                      TEXT PRIMARY KEY,
        type                    TEXT NOT NULL,
        client_id               TEXT NOT NULL,
        client_secret_enc       TEXT NOT NULL,
        project_id              TEXT,
        environment             TEXT DEFAULT 'production',
        default_external_user_id TEXT DEFAULT 'default',
        created_at              REAL DEFAULT (unixepoch())
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS oauth_broker_accounts (
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
    CREATE TABLE IF NOT EXISTS oauth_broker_connect_labels (
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
    CREATE TABLE IF NOT EXISTS api_broker_apps (
        api_id          TEXT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
        broker_id       TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        broker_app_id   TEXT NOT NULL,
        PRIMARY KEY (api_id, broker_id)
    )
    """)

    # ── Seed Data ────────────────────────────────────────────────────────

    # Default toolkit (used by admin key)
    op.execute("""
    INSERT OR IGNORE INTO toolkits (id, name, description, api_key)
    VALUES ('default', 'Default', 'System default toolkit — used by the admin key', 'ADMIN_KEY_SENTINEL')
    """)

    # Note: the legacy backfill of toolkit_keys from toolkits.api_key is not
    # needed here. On a fresh DB the only toolkit is the default (which uses
    # ADMIN_KEY_SENTINEL, not a real key). On pre-existing DBs the old
    # init_db() already ran this backfill before Alembic was introduced.


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.execute("DROP TABLE IF EXISTS api_broker_apps")
    op.execute("DROP TABLE IF EXISTS oauth_broker_connect_labels")
    op.execute("DROP TABLE IF EXISTS oauth_broker_accounts")
    op.execute("DROP TABLE IF EXISTS oauth_brokers")
    op.execute("DROP TABLE IF EXISTS api_overlays")
    op.execute("DROP TABLE IF EXISTS settings")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TABLE IF EXISTS execution_steps")
    op.execute("DROP TABLE IF EXISTS executions")
    op.execute("DROP TABLE IF EXISTS notes")
    op.execute("DROP TABLE IF EXISTS auth_override_log")
    op.execute("DROP TABLE IF EXISTS workflows")
    op.execute("DROP TABLE IF EXISTS permission_requests")
    op.execute("DROP TABLE IF EXISTS api_keys")
    op.execute("DROP TABLE IF EXISTS credential_policies")
    op.execute("DROP TABLE IF EXISTS toolkit_policies")
    op.execute("DROP TABLE IF EXISTS toolkit_keys")
    op.execute("DROP TABLE IF EXISTS toolkit_credentials")
    op.execute("DROP TABLE IF EXISTS toolkits")
    op.execute("DROP TABLE IF EXISTS credentials")
    op.execute("DROP TABLE IF EXISTS operations")
    op.execute("DROP TABLE IF EXISTS apis")
