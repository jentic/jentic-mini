"""
startup.py — Jentic Mini self-registration

On first boot (or when the registration is missing), Jentic Mini:
  1. Imports its own OpenAPI spec into the catalog
  2. Creates an internal credential (admin toolkit key) in the vault

Both operations are idempotent — safe to call on every startup.

See docs/SELF-REGISTRATION.md for design rationale.
"""
import asyncio
import json
import logging
import os
import pathlib
import secrets
import uuid

from src.db import get_db
from src.brokers.pipedream import _API_ID_TO_PD_SLUG as _PIPEDREAM_APP_SEEDS
from src.config import JENTIC_PUBLIC_HOSTNAME, DATA_DIR, SPECS_DIR

_REGISTER_INSTALL_URL = "https://api.jentic.com/api/v1/register-install"
_INSTALL_ID_FILE = DATA_DIR / "install-id.txt"
_INSTALL_REGISTERED_FILE = DATA_DIR / "install-registered.txt"

log = logging.getLogger("jentic")

_INTERNAL_CRED_ID   = "jentic-mini"          # vault credential ID
_INTERNAL_PORT      = int(os.getenv("JENTIC_INTERNAL_PORT", "8900"))


def _public_hostname() -> str:
    return JENTIC_PUBLIC_HOSTNAME


async def self_register(app=None) -> None:
    """Schedule self-registration as a background task so it doesn't block startup."""
    async def _run():
        # Small delay to ensure the server is fully ready before we generate the spec
        await asyncio.sleep(2)
        await _ensure_spec_imported(app)
        await _ensure_internal_credential()
        await register_install()

    asyncio.create_task(_run())


# ── Install registration ──────────────────────────────────────────────────────

async def register_install() -> None:
    """On first startup, generate a random install ID and register it with Jentic.

    The install ID is a random UUID stored in DATA_DIR/install-id.txt. A second
    local marker file, DATA_DIR/install-registered.txt, is written after a
    successful registration so that future startups can skip the network call.

    The JSON payload sent to Jentic contains only this UUID ({"id": "<uuid>"}).
    No additional device, host, or user metadata is included in the payload.
    As with any outbound HTTP request, the server and intermediate network
    infrastructure may observe and log the client IP address in standard logs.
    The ID is used to count installs and, in future, to enable community
    contribution features (workflow sharing, API fix contributions).

    Set JENTIC_TELEMETRY=off to skip the registration HTTP request. The install
    ID file is still created for idempotency, but no registration payload is
    sent to Jentic and the install-registered marker is not written.
    """
    # Ensure data dir exists
    _INSTALL_ID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load or create the install ID (never deleted — stable across restarts)
    if _INSTALL_ID_FILE.exists():
        raw = _INSTALL_ID_FILE.read_text().strip()
        try:
            # Validate and normalize as UUID; this raises ValueError on invalid/empty input
            install_uuid = uuid.UUID(raw)
            install_id = str(install_uuid)
        except (ValueError, TypeError, AttributeError):
            # Regenerate if file is empty or corrupted and overwrite on disk
            install_id = str(uuid.uuid4())
            _INSTALL_ID_FILE.write_text(install_id)
            log.info("register_install: regenerated invalid install ID %s", install_id)
    else:
        install_id = str(uuid.uuid4())
        _INSTALL_ID_FILE.write_text(install_id)
        log.debug("register_install: new install ID (truncated) %s...", install_id[:8])

    # Already successfully registered on a previous startup — nothing to do
    if _INSTALL_REGISTERED_FILE.exists():
        log.debug("register_install: already registered — skipping")
        return

    # Opt-out check
    if os.environ.get("JENTIC_TELEMETRY", "").lower() == "off":
        log.info("register_install: telemetry disabled (JENTIC_TELEMETRY=off) — skipping")
        return

    # Fire the registration call
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _REGISTER_INSTALL_URL,
                json={"id": install_id},
            )
            if resp.is_success:
                _INSTALL_REGISTERED_FILE.write_text(install_id)
                log.info("register_install: registered successfully")
            else:
                log.warning("register_install: server returned %d — will retry on next startup", resp.status_code)
    except Exception as exc:
        log.warning("register_install: network call failed (%s) — will retry on next startup", exc)


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
        specs_dir = SPECS_DIR
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
            scheme={"in": "header", "name": "X-Jentic-API-Key"},
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
            from src.auth import default_allowed_ips
            allowed_ips = json.dumps(default_allowed_ips())
            await db.execute(
                """INSERT OR IGNORE INTO toolkit_keys
                   (id, toolkit_id, api_key, label, allowed_ips, created_at)
                   VALUES (?, ?, ?, 'Jentic Mini Internal Key', ?, unixepoch())""",
                ("ck_internal", DEFAULT_TOOLKIT_ID, raw_key, allowed_ips),
            )
            await db.commit()

        log.info(
            "self-registration: internal credential created (id=%s, toolkit=%s)",
            _INTERNAL_CRED_ID,
            DEFAULT_TOOLKIT_ID,
        )
    except Exception as exc:
        log.warning("self-registration: credential creation failed — %s", exc)



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



async def _backfill_credential_routes() -> None:
    """Ensure every credential has at least one entry in credential_routes.

    Credentials created before migration 0006 may not have rows in credential_routes.
    This idempotent backfill adds route entries derived from api_id for any
    credential with no existing credential_routes rows.

    Runs at every startup — the LEFT JOIN makes it a no-op if already complete.
    """
    from src.vault import _parse_route
    import json as _json
    async with get_db() as db:
        async with db.execute(
            """SELECT c.id, c.api_id
               FROM credentials c
               LEFT JOIN credential_routes cr ON c.id = cr.credential_id
               WHERE cr.credential_id IS NULL"""
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        log.debug("_backfill_credential_routes: nothing to backfill")
        return

    log.info("_backfill_credential_routes: backfilling routes for %d credential(s)", len(rows))
    async with get_db() as db:
        for cred_id, api_id in rows:
            if not api_id:
                continue
            host, path_prefix = _parse_route(api_id)
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host, path_prefix) VALUES (?,?,?)",
                (cred_id, host, path_prefix),
            )
        await db.commit()
    log.info("_backfill_credential_routes: done")
