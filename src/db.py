"""Database initialisation and connection helper."""
import os
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "/app/data/jentic-mini.db")

_CREATE = [
    # Core API Registry
    """
    CREATE TABLE IF NOT EXISTS apis (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        spec_path   TEXT,
        base_url    TEXT,
        created_at  REAL DEFAULT (unixepoch())
    )
    """,
    """
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
    """,

    # Credential Vault
    """
    CREATE TABLE IF NOT EXISTS credentials (
        id              TEXT PRIMARY KEY,
        label           TEXT NOT NULL,
        env_var         TEXT UNIQUE,  -- internal slug only, not exposed via API
        encrypted_value TEXT NOT NULL,
        created_at      REAL DEFAULT (unixepoch()),
        updated_at      REAL DEFAULT (unixepoch())
    )
    """,

    # Toolkits: scoped credential bundles with their own API keys
    """
    CREATE TABLE IF NOT EXISTS toolkits (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        api_key     TEXT NOT NULL UNIQUE,
        simulate    INTEGER NOT NULL DEFAULT 0,
        created_at  REAL DEFAULT (unixepoch()),
        updated_at  REAL DEFAULT (unixepoch())
    )
    """,

    # Credentials granted to a toolkit (with optional alias for disambiguation)
    """
    CREATE TABLE IF NOT EXISTS toolkit_credentials (
        id            TEXT PRIMARY KEY,
        toolkit_id TEXT NOT NULL REFERENCES toolkits(id) ON DELETE CASCADE,
        credential_id TEXT NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
        alias         TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        UNIQUE (toolkit_id, credential_id)
    )
    """,

    # Access keys per toolkit — one toolkit can have many keys (one per agent).
    # Each key can be individually revoked without affecting other agents on the same toolkit.
    # allowed_ips: JSON array of IPv4/IPv6/CIDR strings, or NULL = unrestricted.
    """
    CREATE TABLE IF NOT EXISTS toolkit_keys (
        id          TEXT PRIMARY KEY,
        toolkit_id TEXT NOT NULL REFERENCES toolkits(id) ON DELETE CASCADE,
        api_key     TEXT NOT NULL UNIQUE,
        label       TEXT,
        allowed_ips TEXT,
        created_at  REAL DEFAULT (unixepoch()),
        revoked_at  REAL
    )
    """,

    # Access control policy per toolkit (default_action + rules JSON)
    """
    CREATE TABLE IF NOT EXISTS toolkit_policies (
        id             TEXT PRIMARY KEY,
        toolkit_id  TEXT NOT NULL UNIQUE REFERENCES toolkits(id) ON DELETE CASCADE,
        default_action TEXT NOT NULL DEFAULT 'allow',
        rules          TEXT NOT NULL DEFAULT '[]',
        summary        TEXT,
        created_at     REAL DEFAULT (unixepoch()),
        updated_at     REAL DEFAULT (unixepoch())
    )
    """,

    # Credential-level permissions: per-credential allow/deny rules
    """
    CREATE TABLE IF NOT EXISTS credential_policies (
        id            TEXT PRIMARY KEY,
        credential_id TEXT NOT NULL UNIQUE REFERENCES credentials(id) ON DELETE CASCADE,
        rules         TEXT NOT NULL DEFAULT '[]',
        summary       TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        updated_at    REAL DEFAULT (unixepoch())
    )
    """,

    # API keys with explicit scopes (execute | contribute | toolkit:write | policy:write | admin)
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id          TEXT PRIMARY KEY,
        api_key     TEXT NOT NULL UNIQUE,
        label       TEXT NOT NULL,
        scopes      TEXT NOT NULL DEFAULT '["execute"]',
        owner_type  TEXT NOT NULL DEFAULT 'agent',
        created_at  REAL DEFAULT (unixepoch()),
        last_used   REAL
    )
    """,

    # Permission requests: agents request scope escalation (requires human approval)
    """
    CREATE TABLE IF NOT EXISTS permission_requests (
        id            TEXT PRIMARY KEY,
        toolkit_id TEXT REFERENCES toolkits(id) ON DELETE CASCADE,
        api_key_id    TEXT,
        type          TEXT NOT NULL,
        payload       TEXT NOT NULL DEFAULT '{}',
        reason        TEXT,
        status        TEXT NOT NULL DEFAULT 'pending',
        user_url      TEXT,
        created_at    REAL DEFAULT (unixepoch()),
        resolved_at   REAL
    )
    """,

    # Execution trace log (W3C Trace Context compatible)
    """
    CREATE TABLE IF NOT EXISTS executions (
        id             TEXT PRIMARY KEY,
        toolkit_id  TEXT,
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
    """,

    # Agent notes/feedback on any resource
    """
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
    """,

    # Auth override observability log
    """
    CREATE TABLE IF NOT EXISTS auth_override_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id       TEXT,
        operation_id TEXT,
        workflow_id  TEXT,
        header_names TEXT NOT NULL,
        success      INTEGER NOT NULL DEFAULT 0,
        created_at   REAL DEFAULT (unixepoch())
    )
    """,
    # Workflows: Arazzo-based multi-step workflows
    """
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
    """,
    # Workflow step-level trace data
    """
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
    """,

    # Async job handles — created when Prefer: wait=N elapses or x-async workflow step detected
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id              TEXT PRIMARY KEY,
        kind            TEXT NOT NULL DEFAULT 'workflow',
        slug_or_id      TEXT NOT NULL,
        toolkit_id   TEXT,
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
    """,

    # Human user account — single root account per instance
    """
    CREATE TABLE IF NOT EXISTS users (
        id            TEXT PRIMARY KEY,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at    REAL DEFAULT (unixepoch())
    )
    """,

    # Instance settings — key/value store for flags and secrets
    # Keys: jwt_secret, default_key_claimed, account_created
    """
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,

    # OpenAPI overlays: client-contributed security scheme patches for APIs
    # that don't define auth in their spec. Once confirmed working by the
    # broker, the overlay is merged into all future spec serves for that API.
    """
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
    """,

    # API ↔ OAuth broker mapping: for a given API, which broker handles auth and
    # what does that broker call the app?
    """
    CREATE TABLE IF NOT EXISTS api_broker_apps (
        api_id          TEXT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
        broker_id       TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        broker_app_id   TEXT NOT NULL,
        PRIMARY KEY (api_id, broker_id)
    )
    """,

    # OAuthBroker: platform-level OAuth provider configs (e.g. Pipedream Connect)
    """
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
    """,

    # OAuthBroker accounts: per-user, per-host connected account mappings
    """
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
        UNIQUE(broker_id, external_user_id, api_host)
    )
    """,

    # Pending labels for connect-link flows: stored at connect-link time,
    # consumed by sync to name the resulting credential.
    """
    CREATE TABLE IF NOT EXISTS oauth_broker_connect_labels (
        id               TEXT PRIMARY KEY,
        broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
        external_user_id TEXT NOT NULL,
        app_slug         TEXT NOT NULL,
        label            TEXT NOT NULL,
        created_at       REAL DEFAULT (unixepoch()),
        UNIQUE(broker_id, external_user_id, app_slug)
    )
    """,
]

# Fixed ID for the default toolkit — maps to admin key access
DEFAULT_TOOLKIT_ID = "default"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        for stmt in _CREATE:
            await db.execute(stmt)
        # Migrations — ADD COLUMN is idempotent via try/except
        migrations = [
            "ALTER TABLE apis ADD COLUMN base_url TEXT",
            "ALTER TABLE operations ADD COLUMN jentic_id TEXT",
            "ALTER TABLE workflows ADD COLUMN involved_apis TEXT",
            # dry_run → simulate rename (add new column, keep old for compat)
            "ALTER TABLE toolkits ADD COLUMN simulate INTEGER NOT NULL DEFAULT 0",
            # IP allowlist: JSON array of CIDR/IP strings, or NULL = unrestricted
            "ALTER TABLE toolkits ADD COLUMN allowed_ips TEXT",
            # Credential → API association
            "ALTER TABLE credentials ADD COLUMN api_id TEXT",
            "ALTER TABLE credentials ADD COLUMN scheme_name TEXT",
            # collection → toolkit table renames (for existing DBs created before this rename)
            "ALTER TABLE collections RENAME TO toolkits",
            "ALTER TABLE collection_keys RENAME TO toolkit_keys",
            "ALTER TABLE collection_credentials RENAME TO toolkit_credentials",
            "ALTER TABLE collection_policies RENAME TO toolkit_policies",
            # collection_id column renames in related tables
            "ALTER TABLE toolkit_keys RENAME COLUMN collection_id TO toolkit_id",
            "ALTER TABLE toolkit_credentials RENAME COLUMN collection_id TO toolkit_id",
            "ALTER TABLE toolkit_policies RENAME COLUMN collection_id TO toolkit_id",
            "ALTER TABLE permission_requests RENAME COLUMN collection_id TO toolkit_id",
            "ALTER TABLE executions RENAME COLUMN collection_id TO toolkit_id",
            "ALTER TABLE jobs RENAME COLUMN collection_id TO toolkit_id",
            # Update timestamp on credentials
            "ALTER TABLE credentials ADD COLUMN updated_at REAL",
            # workspace_id was a brief rename — ensure column is called project_id
            "ALTER TABLE oauth_brokers RENAME COLUMN workspace_id TO project_id",
            # Pipedream: label column for connected accounts (display name per account)
            "ALTER TABLE oauth_broker_accounts ADD COLUMN label TEXT",
            # api_broker_apps: handled by CREATE TABLE IF NOT EXISTS above (no ALTER needed)
            # Credential identity field (username / client_id / account SID etc.)
            "ALTER TABLE credentials ADD COLUMN identity TEXT",

            # Rename scheme_name → auth_type; normalise values to bearer/basic/apiKey/pipedream_oauth
            "ALTER TABLE credentials RENAME COLUMN scheme_name TO auth_type",
            """UPDATE credentials SET auth_type = CASE
                   WHEN auth_type IN ('BearerAuth', 'bearer') THEN 'bearer'
                   WHEN auth_type IN ('BasicAuth', 'basic') THEN 'basic'
                   WHEN auth_type IS NOT NULL AND auth_type NOT IN ('bearer', 'basic', 'pipedream_oauth') THEN 'apiKey'
                   ELSE auth_type
               END""",
        ]
        for m in migrations:
            try:
                await db.execute(m)
            except Exception:
                pass  # column already exists

        # Ensure toolkit_keys table exists (CREATE IF NOT EXISTS handles this)
        # Seed toolkit_keys from toolkits.api_key for backward compat —
        # each existing toolkit gets a single key entry called "Default key".
        await db.execute("""
            INSERT OR IGNORE INTO toolkit_keys (id, toolkit_id, api_key, label, allowed_ips, created_at)
            SELECT 'ck_' || id, id, api_key, 'Default key', allowed_ips, created_at
            FROM toolkits
            WHERE api_key != 'ADMIN_KEY_SENTINEL'
              AND api_key IS NOT NULL
        """)
        await db.commit()

        # Ensure the default toolkit exists (used by admin key)
        await db.execute(
            """
            INSERT OR IGNORE INTO toolkits (id, name, description, api_key)
            VALUES (?, 'Default', 'System default toolkit — used by the admin key', 'ADMIN_KEY_SENTINEL')
            """,
            (DEFAULT_TOOLKIT_ID,),
        )
        await db.commit()

        # Migrate legacy coll_xxxxxxxx toolkit IDs → name-derived hyphen slugs (one-time).
        # Safe to re-run: only touches rows whose id starts with 'coll_'.
        import re as _re

        def _slugify(name: str) -> str:
            slug = name.lower()
            slug = _re.sub(r"[^a-z0-9]+", "-", slug)
            return slug.strip("-") or "toolkit"

        async with db.execute("SELECT id, name FROM toolkits WHERE id LIKE 'coll_%'") as cur:
            legacy_rows = await cur.fetchall()

        for old_id, name in legacy_rows:
            new_id = _slugify(name)
            # Avoid collision with an existing slug
            async with db.execute("SELECT id FROM toolkits WHERE id=? AND id!=?", (new_id, old_id)) as cur:
                if await cur.fetchone():
                    new_id = new_id + "-" + old_id[-4:]  # disambiguate with last 4 chars
            # Must disable FK checks: updating the PK in toolkits while FKs are on would fail.
            # Update FK tables first, then the PK row.
            await db.execute("PRAGMA foreign_keys = OFF")
            for tbl, col in [
                ("toolkit_keys",         "toolkit_id"),
                ("toolkit_credentials",  "toolkit_id"),
                ("toolkit_policies",     "toolkit_id"),
                ("access_requests",      "toolkit_id"),
                ("executions",           "toolkit_id"),
                ("jobs",                 "toolkit_id"),
                ("toolkits",             "id"),           # PK last
            ]:
                try:
                    await db.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (new_id, old_id))
                except Exception:
                    pass  # table may not exist
            await db.execute("PRAGMA foreign_keys = ON")

        await db.commit()

        # Migrate legacy UUID credential IDs → semantic slugs (one-time).
        # Format: api_id[-remainder] where remainder is label with api tokens + common words stripped.
        # E.g. api.elevenlabs.io + "ElevenLabs API Key" → "api.elevenlabs.io"
        #      api.github.com    + "GitHub PAT"         → "api.github.com-pat"
        import re as _re2

        def _cred_slug(api_id: str | None, label: str) -> str:
            if not api_id:
                # No api_id — just slugify the label
                return _re2.sub(r"[^a-z0-9.-]+", "-", label.lower()).strip("-") or "credential"
            _COMMON = {"api", "key", "token", "secret", "auth", "oauth",
                       "credential", "credentials", "access", "the", "a", "an"}
            api_tokens = set(_re2.split(r"[./\-_]", api_id.lower())) | _COMMON
            label_parts = _re2.split(r"[\s\-_./]+", label.lower())
            remainder = [p for p in label_parts if p and p not in api_tokens]
            if remainder:
                suffix = _re2.sub(r"[^a-z0-9]+", "-", "-".join(remainder)).strip("-")
                return f"{api_id}-{suffix}" if suffix else api_id
            return api_id

        # Only migrate UUIDs (8-4-4-4-12 pattern)
        _UUID_RE = _re2.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        async with db.execute("SELECT id, label, api_id FROM credentials") as cur:
            cred_rows = await cur.fetchall()

        for old_cid, label, api_id in cred_rows:
            if not _UUID_RE.match(old_cid):
                continue  # already migrated
            base_slug = _cred_slug(api_id, label)
            new_cid = base_slug
            # Handle collisions
            suffix_n = 2
            while True:
                async with db.execute(
                    "SELECT id FROM credentials WHERE id=? AND id!=?", (new_cid, old_cid)
                ) as cur:
                    if not await cur.fetchone():
                        break
                new_cid = f"{base_slug}-{suffix_n}"
                suffix_n += 1

            await db.execute("PRAGMA foreign_keys = OFF")
            for tbl, col in [
                ("toolkit_credentials",  "credential_id"),
                ("credential_policies",  "credential_id"),
                ("credentials",          "id"),
            ]:
                try:
                    await db.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (new_cid, old_cid))
                except Exception:
                    pass
            await db.execute("PRAGMA foreign_keys = ON")

        await db.commit()


def get_db() -> aiosqlite.Connection:
    """Return an async context-manager for a DB connection."""
    return aiosqlite.connect(DB_PATH)


async def get_setting(key: str) -> str | None:
    """Read a single settings value."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    """Write a single settings value."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()


async def setup_state() -> dict:
    """Return current setup flags as a dict.

    Keys:
      default_key_claimed — bool
      account_created     — bool
      jwt_secret          — str (generated on first call)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
    s = {r[0]: r[1] for r in rows}

    # Generate jwt_secret on first call
    if "jwt_secret" not in s:
        import secrets
        secret = secrets.token_hex(32)
        await set_setting("jwt_secret", secret)
        s["jwt_secret"] = secret

    return {
        "default_key_claimed": s.get("default_key_claimed") == "1",
        "account_created": s.get("account_created") == "1",
        "jwt_secret": s["jwt_secret"],
    }
