"""
startup.py — Jentic Mini self-registration

On first boot (or when the registration is missing), Jentic Mini:
  1. Imports its own OpenAPI spec into the catalog
  2. Creates an internal credential (admin toolkit key) in the vault

Both operations are idempotent — safe to call on every startup.

See docs/SELF-REGISTRATION.md for design rationale.
"""
import asyncio
import logging
import os
import secrets

from src.db import get_db

log = logging.getLogger("jentic")

_INTERNAL_CRED_ID   = "jentic-mini"          # vault credential ID
_INTERNAL_PORT      = int(os.getenv("JENTIC_INTERNAL_PORT", "8900"))


def _public_hostname() -> str:
    return (
        os.environ.get("JENTIC_PUBLIC_HOSTNAME")
        or "jentic-mini.home.seanblanchfield.com"
    )


async def self_register(app=None) -> None:
    """Schedule self-registration as a background task so it doesn't block startup."""
    async def _run():
        # Small delay to ensure the server is fully ready before we generate the spec
        await asyncio.sleep(2)
        await _ensure_spec_imported(app)
        await _ensure_internal_credential()

    asyncio.create_task(_run())


# ── Step 1: import own OpenAPI spec ──────────────────────────────────────────

async def _ensure_spec_imported(app=None) -> None:
    """Import Jentic Mini's own OpenAPI spec into the catalog (skip if already present)."""
    hostname = _public_hostname()
    async with get_db() as db:
        # Clean up stale short-ID entries from before the hostname-based ID was adopted
        await db.execute(
            "DELETE FROM apis WHERE id='jentic-mini'",
        )
        await db.commit()
        async with db.execute(
            "SELECT id FROM apis WHERE id=?", (hostname,)
        ) as cur:
            if await cur.fetchone():
                log.info("self-registration: spec already imported — skipping")
                return

    log.info("self-registration: importing own OpenAPI spec")
    try:
        # Build the spec directly (same logic as custom_openapi in main.py)
        # We don't call app.openapi() to avoid caching issues during lifespan.
        if app is None:
            raise ValueError("app instance required for spec import")
        from fastapi.openapi.utils import get_openapi as _get_openapi
        spec = _get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Force the server URL to the public hostname so broker routing works
        hostname = _public_hostname()
        spec["servers"] = [{"url": f"https://{hostname}"}]

        from src.routers.import_ import _register_openapi
        import json, pathlib
        specs_dir = pathlib.Path("/app/data/specs")
        specs_dir.mkdir(parents=True, exist_ok=True)
        saved_path = str(specs_dir / "jentic-mini.json")
        pathlib.Path(saved_path).write_text(json.dumps(spec))

        result = await _register_openapi(spec, saved_path)
        # The api_id is derived from the server URL (JENTIC_PUBLIC_HOSTNAME),
        # which is already the canonical ID we want for broker routing.
        log.info(
            "self-registration: spec imported (%d operations, id=%s)",
            result["operations_indexed"],
            result["id"],
        )
    except Exception as exc:
        import traceback
        log.warning("self-registration: spec import failed — %s\n%s", exc, traceback.format_exc())


# ── Step 2: create internal admin credential ──────────────────────────────────

async def _ensure_internal_credential() -> None:
    """Create a Jentic Mini admin credential in the vault (skip if already present)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM credentials WHERE id=?", (_INTERNAL_CRED_ID,)
        ) as cur:
            if await cur.fetchone():
                log.info("self-registration: internal credential already exists — skipping")
                return

    log.info("self-registration: creating internal admin credential")
    try:
        # Generate a fresh admin toolkit key
        raw_key = "tk_" + secrets.token_hex(16)

        # Store it in the vault
        from src.vault import create_credential
        cred = await create_credential(
            label="Jentic Mini Admin Key",
            env_var="JENTIC_MINI_ADMIN_KEY",
            value=raw_key,
            api_id=_public_hostname(),
            scheme_name="JenticApiKey",
        )

        # Override the semantic ID to our canonical internal ID (in case slug differs)
        if cred["id"] != _INTERNAL_CRED_ID:
            async with get_db() as db:
                await db.execute(
                    "UPDATE credentials SET id=? WHERE id=?",
                    (_INTERNAL_CRED_ID, cred["id"]),
                )
                await db.commit()

        # Register the key as a valid toolkit key in the DB (bound to default toolkit)
        async with get_db() as db:
            from src.db import DEFAULT_TOOLKIT_ID
            from src.auth import default_allowed_ips_json
            allowed_ips = default_allowed_ips_json()
            await db.execute(
                """INSERT OR IGNORE INTO toolkit_keys
                   (id, toolkit_id, label, allowed_ips_json, created_at)
                   VALUES (?, ?, 'Jentic Mini Internal Key', ?, unixepoch())""",
                (raw_key, DEFAULT_TOOLKIT_ID, allowed_ips),
            )
            await db.commit()

        log.info(
            "self-registration: internal credential created (id=%s, toolkit=%s)",
            _INTERNAL_CRED_ID,
            DEFAULT_TOOLKIT_ID,
        )
    except Exception as exc:
        log.warning("self-registration: credential creation failed — %s", exc)


# ── Broker app seed ───────────────────────────────────────────────────────────

# Maps our api_id (hostname-derived) → Pipedream app slug.
_PIPEDREAM_APP_SEEDS: dict[str, str] = {
    "gmail.googleapis.com":        "gmail",
    "www.googleapis.com":          "gmail",
    "calendar.googleapis.com":     "google_calendar",
    "people.googleapis.com":       "google_people",
    "sheets.googleapis.com":       "google_sheets",
    "docs.googleapis.com":         "google_docs",
    "drive.googleapis.com":        "google_drive",
    "slides.googleapis.com":       "google_slides",
    "oauth2.googleapis.com":       "google",
    "admin.googleapis.com":        "google_admin",
    "api.github.com":              "github",
    "slack.com":                   "slack",
    "api.slack.com":               "slack",
    "api.stripe.com":              "stripe",
    "api.twilio.com":              "twilio",
    "api.hubapi.com":              "hubspot",
    "salesforce.com":              "salesforce_rest_api",
    "api.intercom.io":             "intercom",
    "api.notion.com":              "notion",
    "api.airtable.com":            "airtable",
    "api.atlassian.com":           "jira",
    "atlassian.net":               "jira",
    "api.linear.app":              "linear_app",
    "discord.com":                 "discord",
    "api.zoom.us":                 "zoom",
    "myshopify.com":               "shopify",
    "api.xero.com":                "xero",
    "api.dropboxapi.com":          "dropbox",
    "api.box.com":                 "box",
    "api.twitter.com":             "twitter",
    "api.x.com":                   "twitter",
    "api.linkedin.com":            "linkedin",
    "app.asana.com/api":           "asana",
    "api.trello.com":              "trello",
    "api.monday.com":              "monday",
    "api.pipedrive.com":           "pipedrive",
    "zendesk.com":                 "zendesk",
    "freshdesk.com":               "freshdesk",
    "api.sendgrid.com":            "sendgrid",
    "api.mailchimp.com":           "mailchimp",
    "api.spotify.com":             "spotify",
    "api.typeform.com":            "typeform",
    "api.openai.com":              "openai",
}


async def seed_broker_apps(broker_id: str = "pipedream") -> None:
    """Upsert api_broker_apps for all known API→Pipedream slug mappings.

    Called automatically at startup (after init_db). Idempotent — safe to run
    on every boot. Skips silently if no broker with the given id is configured.
    """
    async with get_db() as db:
        # Only seed if a matching broker row exists
        async with db.execute(
            "SELECT id FROM oauth_brokers WHERE id=?", (broker_id,)
        ) as cur:
            if not await cur.fetchone():
                log.debug("seed_broker_apps: broker '%s' not configured — skipping", broker_id)
                return

        async with db.execute("SELECT id FROM apis") as cur:
            local_api_ids = {r[0] for r in await cur.fetchall()}

        inserted = updated = 0
        for api_id, broker_app_id in _PIPEDREAM_APP_SEEDS.items():
            if api_id not in local_api_ids:
                continue
            await db.execute(
                """INSERT INTO api_broker_apps (api_id, broker_id, broker_app_id)
                   VALUES (?, ?, ?)
                   ON CONFLICT(api_id, broker_id)
                   DO UPDATE SET broker_app_id=excluded.broker_app_id
                   WHERE broker_app_id != excluded.broker_app_id""",
                (api_id, broker_id, broker_app_id),
            )
            # Track whether this was an insert or a no-op update
            if db.total_changes > (inserted + updated):
                inserted += 1

        await db.commit()
    if inserted or updated:
        log.info("seed_broker_apps: %d inserted, %d updated for broker '%s'", inserted, updated, broker_id)
    else:
        log.debug("seed_broker_apps: all mappings already up-to-date for broker '%s'", broker_id)
