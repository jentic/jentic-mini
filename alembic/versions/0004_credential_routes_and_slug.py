"""Add routes field, replace credential IDs with human-readable slugs, drop api_id.

Breaking change: credential IDs change from opaque values (e.g. 'pipedream-apn_xxx-host')
to human-readable slugs derived from labels (e.g. 'work-gmail'). The api_id column is
replaced by a routes JSON array of host+path prefixes for deterministic broker matching.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-09
"""
import json
import re

from alembic import op
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# ── Slug generation (must be self-contained — no app imports in migrations) ──

_COMMON_WORDS = {"api", "key", "token", "secret", "auth", "oauth", "credential",
                 "credentials", "access", "the", "a", "an", "my", "for"}


def _slugify(label: str) -> str:
    """Generate a URL-safe slug from a label. Lowercase, hyphens, no trailing."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "credential"


def _unique_slug(slug: str, existing: set[str]) -> str:
    """Ensure slug is unique by appending -2, -3, etc."""
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"


# ── Pipedream app_slug → catalog path mapping (subset for route derivation) ──
# Only need the reverse direction: slug → host+path prefix for routes.

_PD_SLUG_TO_ROUTE: dict[str, str] = {
    "gmail": "www.googleapis.com/gmail",
    "google_calendar": "www.googleapis.com/calendar",
    "google_sheets": "sheets.googleapis.com",
    "google_drive": "www.googleapis.com/drive",
    "google_docs": "docs.googleapis.com",
    "google_contacts": "people.googleapis.com",
    "github": "api.github.com",
    "slack": "slack.com/api",
    "stripe": "api.stripe.com",
    "openai": "api.openai.com",
    "discord": "discord.com/api",
    "notion": "api.notion.com",
    "airtable": "api.airtable.com",
    "twilio": "api.twilio.com",
    "sendgrid": "api.sendgrid.com",
    "hubspot": "api.hubapi.com",
    "jira": "api.atlassian.com",
    "linear": "api.linear.app",
    "asana": "app.asana.com/api",
}


def upgrade():
    conn = op.get_bind()

    # ── 1. Read existing credentials ─────────────────────────────────────
    rows = conn.execute(text(
        "SELECT id, label, env_var, encrypted_value, created_at, updated_at, "
        "api_id, auth_type, identity FROM credentials"
    )).fetchall()

    # ── 2. Read oauth_broker_accounts for Pipedream route derivation ─────
    try:
        broker_accounts = conn.execute(text(
            "SELECT account_id, api_host, app_slug FROM oauth_broker_accounts"
        )).fetchall()
    except Exception:
        broker_accounts = []

    # Build account_id → app_slug lookup
    account_slugs: dict[str, str] = {}
    for ba in broker_accounts:
        account_slugs[ba[0]] = ba[2]  # account_id → app_slug

    # ── 3. Generate new IDs and routes ───────────────────────────────────
    used_slugs: set[str] = set()
    id_mapping: dict[str, str] = {}  # old_id → new_id
    migrated: list[dict] = []

    for row in rows:
        old_id, label, env_var, enc_val, created, updated, api_id, auth_type, identity = row

        # Generate new slug-based ID
        new_id = _unique_slug(_slugify(label), used_slugs)
        used_slugs.add(new_id)
        id_mapping[old_id] = new_id

        # Derive routes from api_id
        routes: list[str] = []
        if auth_type == "pipedream_oauth":
            # Try to derive host+path route from Pipedream app_slug
            # Extract account_id from old ID format: {broker_id}-{account_id}-{host_slug}
            parts = old_id.split("-")
            if len(parts) >= 3:
                # account_id is the second part (e.g. "apn_xxx")
                account_id_candidate = parts[1]
                # Handle account_ids with hyphens (e.g. "apn_xxx")
                # The format is: broker_id-account_id-host_slug
                # Since host_slug replaces dots with hyphens, we need to find
                # the account_id from the broker_accounts table
                for acct_id, slug in account_slugs.items():
                    if acct_id in old_id:
                        route = _PD_SLUG_TO_ROUTE.get(slug)
                        if route:
                            routes = [route]
                        break
            if not routes and api_id:
                routes = [api_id]
        elif api_id:
            routes = [api_id]

        migrated.append({
            "id": new_id,
            "label": label,
            "env_var": env_var,
            "encrypted_value": enc_val,
            "created_at": created,
            "updated_at": updated,
            "routes": json.dumps(routes),
            "auth_type": auth_type,
            "identity": identity,
        })

    # ── 4. Disable FK checks during table rebuild ────────────────────────
    conn.execute(text("PRAGMA foreign_keys = OFF"))

    # ── 5. Recreate credentials table with routes, without api_id ────────
    op.execute("DROP TABLE IF EXISTS credentials_new")
    op.execute("""
    CREATE TABLE credentials_new (
        id              TEXT PRIMARY KEY,
        label           TEXT NOT NULL,
        env_var         TEXT UNIQUE,
        encrypted_value TEXT NOT NULL,
        created_at      REAL DEFAULT (unixepoch()),
        updated_at      REAL,
        routes          TEXT NOT NULL DEFAULT '[]',
        auth_type       TEXT,
        identity        TEXT
    )
    """)

    # ── 6. Insert migrated data ──────────────────────────────────────────
    for m in migrated:
        conn.execute(text(
            "INSERT INTO credentials_new "
            "(id, label, env_var, encrypted_value, created_at, updated_at, routes, auth_type, identity) "
            "VALUES (:id, :label, :env_var, :enc, :created, :updated, :routes, :auth_type, :identity)"
        ), {"id": m["id"], "label": m["label"], "env_var": m["env_var"], "enc": m["encrypted_value"],
            "created": m["created_at"], "updated": m["updated_at"], "routes": m["routes"],
            "auth_type": m["auth_type"], "identity": m["identity"]})

    # ── 7. Update FK references ──────────────────────────────────────────
    for old_id, new_id in id_mapping.items():
        conn.execute(text(
            "UPDATE toolkit_credentials SET credential_id=:new WHERE credential_id=:old"
        ), {"new": new_id, "old": old_id})
        conn.execute(text(
            "UPDATE credential_policies SET credential_id=:new WHERE credential_id=:old"
        ), {"new": new_id, "old": old_id})

    # ── 8. Swap tables ───────────────────────────────────────────────────
    op.execute("DROP TABLE credentials")
    op.execute("ALTER TABLE credentials_new RENAME TO credentials")

    # ── 9. Re-enable FK checks ───────────────────────────────────────────
    conn.execute(text("PRAGMA foreign_keys = ON"))


def downgrade():
    """Reverse: add api_id back, remove routes. Slug IDs are kept (no reverse mapping)."""
    conn = op.get_bind()
    conn.execute(text("PRAGMA foreign_keys = OFF"))

    # Read current data
    rows = conn.execute(text(
        "SELECT id, label, env_var, encrypted_value, created_at, updated_at, "
        "routes, auth_type, identity FROM credentials"
    )).fetchall()

    op.execute("DROP TABLE IF EXISTS credentials_old")
    op.execute("ALTER TABLE credentials RENAME TO credentials_old")

    op.execute("""
    CREATE TABLE credentials (
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

    for row in rows:
        cid, label, env_var, enc_val, created, updated, routes_json, auth_type, identity = row
        # Derive api_id from first route entry
        try:
            routes = json.loads(routes_json) if routes_json else []
        except (json.JSONDecodeError, TypeError):
            routes = []
        api_id = routes[0] if routes else None

        conn.execute(text(
            "INSERT INTO credentials "
            "(id, label, env_var, encrypted_value, created_at, updated_at, api_id, auth_type, identity) "
            "VALUES (:id, :label, :env, :enc, :created, :updated, :api_id, :auth, :ident)"
        ), {"id": cid, "label": label, "env": env_var, "enc": enc_val,
            "created": created, "updated": updated, "api_id": api_id,
            "auth": auth_type, "ident": identity})

    op.execute("DROP TABLE credentials_old")
    conn.execute(text("PRAGMA foreign_keys = ON"))
