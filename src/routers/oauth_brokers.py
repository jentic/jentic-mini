"""
/oauth-brokers — manage OAuth broker configurations.

OAuth brokers handle delegated OAuth credential management for APIs where
Jentic doesn't yet have production OAuth app approvals. The broker either
returns a raw token (if the provider exposes it) or proxies requests through
their infrastructure with OAuth injected server-side.

Current broker types:
  pipedream — Pipedream Connect (3,000+ APIs, managed OAuth via proxy)

Future:
  jentic    — Jentic's own OAuth service (once app approvals are in place)
"""
import logging
import time
from typing import Annotated, Any

import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from src.validators import NormModel, NormStr
from src.utils import build_absolute_url

from src.auth import require_human_session
from src.db import get_db
from src.oauth_broker import registry as oauth_broker_registry
import src.vault as vault

log = logging.getLogger("jentic.routers.oauth_brokers")

router = APIRouter(prefix="/oauth-brokers", tags=["credentials"])


# ── Request / Response models ─────────────────────────────────────────────────

_PIPEDREAM_CONFIG_EXAMPLE = {
    "client_id": "oa_abc123",
    "client_secret": "pd_secret_xxxx",
    "project_id": "proj_abc123",
    "support_email": "support@example.com",
}

_SUPPORTED_TYPES = ("pipedream",)

# Annotated path/query helpers with pre-filled Swagger examples
BrokerIdPath = Annotated[str, Path(description="The broker ID", example="pipedream")]
ExternalUserIdQuery = Annotated[str | None, Query(description="Filter by external user ID", example="default")]

_CREATE_EXAMPLE = {
    "type": "pipedream",
    "config": _PIPEDREAM_CONFIG_EXAMPLE,
}

_CREATE_DESCRIPTION = """\
Register a delegated OAuth broker. Currently supported type: `pipedream`.

---

### Pipedream — one-time setup

Before registering, complete these steps in the Pipedream UI:

**1.** Go to [pipedream.com](https://pipedream.com) and sign in or create an account.

**2.** Go to **Settings** (main menu) → **API** → click **+ New OAuth Client**.
Name it "Jentic". Store the **client ID** and **client secret** safely — the secret is not shown again.

**3.** Go to **Projects** (main menu) and click **+ New Project**. Name it "Jentic".

**4.** Go to **Projects → Jentic → Settings** and note the **project ID** (format: `proj_xxx`).

That's it. Register the broker below — Jentic automatically configures the Connect
application name, support email, and logo in Pipedream on your behalf, so you don't
need to touch the Connect → Configuration screen manually.

---

### Registration

```json
{
  "type": "pipedream",
  "config": {
    "client_id": "oa_abc123",
    "client_secret": "pd_secret_xxxx",
    "project_id": "proj_abc123",
    "support_email": "support@example.com"
  }
}
```

`support_email` is optional but recommended — it is displayed to end users in the
Pipedream OAuth consent UI.

`client_secret` is write-only — Fernet-encrypted at rest, never returned.

---

### After registration

Once registered, connect individual apps with `POST /oauth-brokers/{id}/connect-link`
(pass `app` as the Pipedream app slug, e.g. `gmail`, `google_calendar`, `slack`).
After the user completes OAuth, call `POST /oauth-brokers/{id}/sync` to pull the
connected account into Jentic. From that point, requests to that API's host are
automatically proxied with the user's OAuth token injected server-side.
"""


class OAuthBrokerCreate(NormModel):
    id: str | None = Field(None, description="Optional custom broker ID. Auto-generated from type if omitted.")
    type: str = Field(..., description="Broker backend type. Currently supported: `pipedream`.")
    config: dict[str, Any] = Field(
        ...,
        description=(
            "Provider-specific configuration. "
            "For `pipedream`: `client_id`, `client_secret`, `project_id` "
            "(all from Pipedream workspace → API settings → OAuth clients). "
            "Optional: `environment` (`production` or `development`, default `production`), "
            "`support_email`."
        ),
        examples=[_PIPEDREAM_CONFIG_EXAMPLE],
    )

    model_config = {"json_schema_extra": {"example": _CREATE_EXAMPLE}}


class OAuthBrokerOut(BaseModel):
    id: str
    type: str
    config: dict[str, Any]          # provider-specific, never includes secret
    created_at: float
    accounts_discovered: int = 0


class SyncRequest(NormModel):
    external_user_id: str = Field(
        "default",
        description=(
            "The user identity to sync accounts for. In a single-user setup this is "
            "always `default`. In multi-user deployments, pass the Jentic user ID "
            "that was used when the user completed OAuth in Pipedream's hosted UI."
        ),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_out(row: tuple, accounts_discovered: int = 0) -> OAuthBrokerOut:
    broker_id, broker_type, client_id, project_id, default_external_user_id, created_at = row
    return OAuthBrokerOut(
        id=broker_id,
        type=broker_type,
        config={
            "client_id": client_id,
            "project_id": project_id,
            "default_external_user_id": default_external_user_id or "default",
        },
        created_at=created_at,
        accounts_discovered=accounts_discovered,
    )


def _make_broker_id(broker_type: str, existing_ids: list[str]) -> str:
    base = broker_type
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


def _extract_pipedream_config(config: dict) -> tuple[str, str, str, str | None, str]:
    """Extract and validate Pipedream config fields.

    Returns (client_id, client_secret, project_id, support_email, environment).
    app_name and logo_url are set by the backend — not exposed in the API.
    """
    missing = [f for f in ("client_id", "client_secret", "project_id") if not config.get(f)]
    if missing:
        raise HTTPException(
            400,
            f"Missing required Pipedream config fields: {', '.join(missing)}. "
            "Expected: client_id, client_secret, project_id"
        )
    support_email = config.get("support_email") or None
    environment = config.get("environment") or "production"
    return config["client_id"], config["client_secret"], config["project_id"], support_email, environment


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=OAuthBrokerOut,
    summary="Register an OAuth broker",
    description=_CREATE_DESCRIPTION,
    dependencies=[Depends(require_human_session)],
)
async def create_oauth_broker(body: OAuthBrokerCreate):
    if body.type not in _SUPPORTED_TYPES:
        raise HTTPException(400, f"Unsupported broker type: '{body.type}'. Supported: pipedream")

    client_id, client_secret, project_id, support_email, environment = (
        _extract_pipedream_config(body.config)
    )

    async with get_db() as db:
        async with db.execute("SELECT id FROM oauth_brokers") as cur:
            existing_ids = [r[0] for r in await cur.fetchall()]

        broker_id = body.id if body.id and body.id not in existing_ids else _make_broker_id(body.type, existing_ids)
        secret_enc = vault.encrypt(client_secret)

        await db.execute(
            """INSERT INTO oauth_brokers
               (id, type, client_id, client_secret_enc, project_id,
                environment, default_external_user_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (broker_id, body.type, client_id, secret_enc,
             project_id, environment, "default", time.time()),
        )
        await db.commit()

    from src.brokers.pipedream import PipedreamOAuthBroker
    broker = PipedreamOAuthBroker(
        broker_id=broker_id,
        client_id=client_id,
        client_secret=client_secret,
        project_id=project_id,
        environment=environment,
        default_external_user_id="default",
    )
    oauth_broker_registry.register(broker)

    # Configure the Pipedream project (name, email, logo) — best-effort, non-fatal
    try:
        await broker.configure_project(
            app_name="Jentic Mini",
            support_email=support_email,
            logo_url="https://jentic.com/favicon.svg",
        )
    except Exception as exc:
        log.warning("Project configuration failed for broker %s: %s", broker_id, exc)

    accounts_discovered = 0
    try:
        accounts_discovered = await broker.discover_accounts("default")
    except Exception as exc:
        log.warning("Account sync failed for broker %s: %s", broker_id, exc)

    log.info("OAuth broker '%s' registered (%d account mappings)", broker_id, accounts_discovered)

    return OAuthBrokerOut(
        id=broker_id,
        type=body.type,
        config={"client_id": client_id, "project_id": project_id, "default_external_user_id": "default"},
        created_at=time.time(),
        accounts_discovered=accounts_discovered,
    )


@router.get(
    "",
    summary="List registered OAuth brokers",
    tags=["inspect"],
)
async def list_oauth_brokers():
    """Return all registered OAuth brokers as a flat list. `client_secret` is never included.

    Accessible to both agents (toolkit key) and humans (session).
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT id, type, client_id, project_id, default_external_user_id, created_at FROM oauth_brokers"
        ) as cur:
            rows = await cur.fetchall()

    return [_row_to_out(r) for r in rows]


@router.get(
    "/{broker_id}",
    summary="Get an OAuth broker",
    tags=["inspect"],
)
async def get_oauth_broker(broker_id: BrokerIdPath):
    async with get_db() as db:
        async with db.execute(
            "SELECT id, type, client_id, project_id, default_external_user_id, created_at "
            "FROM oauth_brokers WHERE id=?",
            (broker_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, f"OAuth broker '{broker_id}' not found")
    return _row_to_out(row)


class ConnectLinkRequest(NormModel):
    external_user_id: str = Field(
        "default",
        description=(
            "The user identity to generate the connect link for. "
            "In a single-user setup this is always `default`. "
            "Must match the `external_user_id` you use when routing requests."
        ),
    )
    app: str = Field(
        ...,
        description=(
            "The Pipedream app slug to connect (e.g. `gmail`, `slack`, `github`, `stripe`). "
            "Required — Pipedream Connect Links must target a specific app. "
            "Find the slug via `GET /oauth-brokers/{id}/apps` or at pipedream.com/apps."
        ),
        examples=["gmail", "slack", "github"],
    )
    label: str = Field(
        ...,
        description=(
            "A human-readable name for this connection, e.g. `work email` or `personal email`. "
            "Required because Pipedream only returns the app name ('Gmail'), not the account "
            "address — without a label there is no way to distinguish multiple accounts "
            "for the same app. This label is carried through to the resulting credential "
            "in `GET /credentials` and used when provisioning the credential to a toolkit."
        ),
        examples=["work email", "personal email", "main Slack workspace"],
    )
    api_id: str | None = Field(
        None,
        description=(
            "The Jentic catalog API ID this connection maps to (e.g. `googleapis.com/gmail`). "
            "If provided, this overrides the automatic slug-map lookup during sync — the "
            "credential will be registered under exactly this API ID. "
            "Find the right ID via `GET /catalog?q=<name>`. "
            "If omitted, the slug map is used as a fallback (may not match the catalog ID)."
        ),
        examples=["googleapis.com/gmail", "slack.com/api", "api.github.com"],
    )


@router.post(
    "/{broker_id}/connect-link",
    summary="Generate a Pipedream Connect Link for authorising apps",
)
async def create_connect_link(broker_id: BrokerIdPath, body: ConnectLinkRequest, request: Request):
    """Generate a short-lived Pipedream Connect Link URL.

    Visit the returned `connect_link_url` in a browser to authorise SaaS apps
    (e.g. Gmail, Slack, GitHub) via Pipedream's hosted OAuth consent UI.

    After completing the OAuth flow, call `POST /oauth-brokers/{id}/sync` to
    pull the new account into jentic-mini so requests start routing through it.

    The link expires after ~1 hour. Generate a new one if it expires before use.

    Intentionally open to agents (not human-session-only): only a human can
    complete the OAuth flow, so generating the link is safe for agents to initiate.
    Requires at minimum a valid toolkit key or trusted-subnet (admin) access.
    """
    from src.auth import _build_human_only_error
    is_admin = getattr(request.state, "is_admin", False)
    is_human = getattr(request.state, "is_human_session", False)
    has_toolkit = getattr(request.state, "toolkit_id", None) is not None
    if not (is_admin or is_human or has_toolkit):
        raise _build_human_only_error()
    live_broker = next(
        (b for b in oauth_broker_registry.brokers if getattr(b, "broker_id", None) == broker_id),
        None,
    )
    if live_broker is None:
        from src.brokers.pipedream import PipedreamOAuthBroker
        brokers = await PipedreamOAuthBroker.from_db()
        live_broker = next((b for b in brokers if b.broker_id == broker_id), None)
        if live_broker:
            oauth_broker_registry.register(live_broker)

    if live_broker is None:
        raise HTTPException(404, f"OAuth broker '{broker_id}' not found or could not be loaded")

    if not hasattr(live_broker, "create_connect_token"):
        raise HTTPException(400, f"Broker type does not support Connect Links")

    # Build the success redirect URI — Pipedream will append nothing of its own,
    # so we encode all the context we need (label, app, api_id, external_user_id)
    # as query params. The callback endpoint reads these, stores the pending label,
    # triggers a sync, and redirects the user to the credentials UI.
    callback_params = {
        "label": body.label,
        "app": body.app,
        "external_user_id": body.external_user_id,
    }
    if body.api_id:
        callback_params["api_id"] = body.api_id
    callback_path = f"/oauth-brokers/{broker_id}/connect-callback?{urllib.parse.urlencode(callback_params)}"
    success_redirect_uri = build_absolute_url(request, callback_path)

    try:
        result = await live_broker.create_connect_token(
            body.external_user_id,
            success_redirect_uri=success_redirect_uri,
        )
    except Exception as exc:
        raise HTTPException(502, f"Failed to create Pipedream Connect Token: {exc}")

    # Pipedream requires the app slug appended to the connect link URL
    connect_link_url = result["connect_link_url"]
    if "&app=" not in connect_link_url:
        connect_link_url = f"{connect_link_url}&app={body.app}"

    return {
        "broker_id": broker_id,
        "external_user_id": body.external_user_id,
        "app": body.app,
        "connect_link_url": connect_link_url,
        "expires_at": result["expires_at"],
        "next_step": f"Visit connect_link_url in your browser, authorise {body.app}, then the browser will redirect automatically and sync will run",
    }


@router.get(
    "/{broker_id}/connect-callback",
    summary="OAuth connect-link completion callback (browser redirect)",
    include_in_schema=False,  # not a user-facing API endpoint
)
async def connect_callback(
    broker_id: BrokerIdPath,
    request: Request,
    label: str = Query(..., description="Label set at connect-link time"),
    app: str = Query(..., description="Pipedream app slug"),
    external_user_id: str = Query("default"),
    api_id: str | None = Query(None),
):
    """Browser callback after Pipedream OAuth completion.

    Pipedream redirects here once the user successfully authorises an app.
    We write the pending label to oauth_broker_connect_labels (keyed by
    app_slug, as before), trigger a sync immediately, then redirect the
    user to the credentials page of the UI.

    This endpoint is hit by the user's browser — no auth token required.
    Labels come from URL params we encoded at connect-link time, so they
    cannot be spoofed by Pipedream or third parties.
    """
    import uuid as _uuid

    # Write the pending label — safe to INSERT OR REPLACE here because we are
    # processing one completion at a time (browser callback is synchronous
    # from the user's perspective). The race that motivated this redesign was
    # *two links created before either was completed*; at callback time each
    # link fires its own redirect with its own label param.
    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO oauth_broker_connect_labels
               (id, broker_id, external_user_id, app_slug, label, api_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(_uuid.uuid4()), broker_id, external_user_id,
                app, label, api_id, time.time(),
            ),
        )
        await db.commit()

    # Trigger sync immediately so the credential lands before the UI loads
    live_broker = next(
        (b for b in oauth_broker_registry.brokers if getattr(b, "broker_id", None) == broker_id),
        None,
    )
    if live_broker is None:
        from src.brokers.pipedream import PipedreamOAuthBroker
        brokers = await PipedreamOAuthBroker.from_db()
        live_broker = next((b for b in brokers if b.broker_id == broker_id), None)
        if live_broker:
            oauth_broker_registry.register(live_broker)

    if live_broker is not None and hasattr(live_broker, "discover_accounts"):
        try:
            await live_broker.discover_accounts(external_user_id)
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "connect-callback: sync failed for broker %s: %s", broker_id, exc
            )
            # Don't block the redirect — user will see the credential once they
            # manually sync, or on next automatic sync.

    # Redirect to credentials UI
    ui_url = build_absolute_url(request, "/credentials")
    return RedirectResponse(url=ui_url, status_code=302)


@router.post(
    "/{broker_id}/sync",
    summary="Sync connected accounts from the OAuth broker",
)
async def sync_broker_accounts(broker_id: BrokerIdPath, body: SyncRequest, request: Request):
    """Re-fetch connected accounts from the provider and update local mappings.

    Call this after connecting a new app via Pipedream's hosted OAuth UI —
    the new account will appear in subsequent `GET /oauth-brokers/{id}/accounts`
    responses and the broker will start routing requests to it automatically.

    This does **not** affect accounts already connected — it is additive.

    Intentionally open to agents: syncing pulls in credentials the human already
    authorised. No new OAuth flows are initiated.
    """
    from src.auth import _build_human_only_error
    is_admin = getattr(request.state, "is_admin", False)
    is_human = getattr(request.state, "is_human_session", False)
    has_toolkit = getattr(request.state, "toolkit_id", None) is not None
    if not (is_admin or is_human or has_toolkit):
        raise _build_human_only_error()

    async with get_db() as db:
        async with db.execute("SELECT type FROM oauth_brokers WHERE id=?", (broker_id,)) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, f"OAuth broker '{broker_id}' not found")

    live_broker = next(
        (b for b in oauth_broker_registry.brokers if getattr(b, "broker_id", None) == broker_id),
        None,
    )
    if live_broker is None:
        from src.brokers.pipedream import PipedreamOAuthBroker
        brokers = await PipedreamOAuthBroker.from_db()
        live_broker = next((b for b in brokers if b.broker_id == broker_id), None)
        if live_broker:
            oauth_broker_registry.register(live_broker)

    if live_broker is None:
        raise HTTPException(500, "Broker found in DB but could not be instantiated")

    try:
        count = await live_broker.discover_accounts(body.external_user_id)
    except Exception as exc:
        raise HTTPException(502, f"Sync failed: {exc}")

    # Return the credential IDs created/updated so the caller knows what to provision
    async with get_db() as db:
        async with db.execute(
            "SELECT id, label, api_id FROM credentials WHERE auth_type='pipedream_oauth' "
            "AND api_id IN (SELECT api_host FROM oauth_broker_accounts "
            "WHERE broker_id=? AND external_user_id=?)",
            (broker_id, body.external_user_id),
        ) as cur:
            cred_rows = await cur.fetchall()

    credentials = [{"id": r[0], "label": r[1], "api_host": r[2]} for r in cred_rows]

    return {
        "broker_id": broker_id,
        "external_user_id": body.external_user_id,
        "accounts_synced": count,
        "credentials": credentials,
        "next_step": (
            "Provision a credential to a toolkit: "
            "POST /toolkits/{toolkit_id}/credentials with {credential_id}"
        ),
        "status": "ok",
    }


@router.get(
    "/{broker_id}/accounts",
    summary="List connected accounts for an OAuth broker",
    tags=["inspect"],
)
async def list_broker_accounts(broker_id: BrokerIdPath, external_user_id: ExternalUserIdQuery = None):
    """List the OAuth-connected account mappings stored for this broker.

    Each entry represents a SaaS app the user has connected via Pipedream's OAuth
    UI, along with the API host it maps to and the Pipedream `account_id` used when
    routing requests through the proxy.

    Use `POST /oauth-brokers/{id}/sync` to refresh this list from Pipedream.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM oauth_brokers WHERE id=?", (broker_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"OAuth broker '{broker_id}' not found")

        query = (
            "SELECT external_user_id, api_host, app_slug, account_id, label, healthy, synced_at "
            "FROM oauth_broker_accounts WHERE broker_id=?"
        )
        params: tuple = (broker_id,)
        if external_user_id:
            query += " AND external_user_id=? ORDER BY api_host"
            params = (broker_id, external_user_id)
        else:
            query += " ORDER BY external_user_id, api_host"

        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()

    cols = ["external_user_id", "api_host", "app_slug", "account_id", "label", "healthy", "synced_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.delete(
    "/{broker_id}/accounts/{api_host:path}",
    summary="Remove a connected account from an OAuth broker",
    dependencies=[Depends(require_human_session)],
)
async def delete_broker_account(broker_id: BrokerIdPath, api_host: str, external_user_id: ExternalUserIdQuery = None):
    """Remove a specific connected account from this broker.

    This performs three actions in order:
    1. Revokes the account in the upstream provider (Pipedream) via their API
    2. Removes the associated credential from all toolkit provisioning
    3. Deletes the credential from the vault and the account from the local DB

    If the Pipedream revoke fails, the local cleanup still proceeds (with a warning).
    """
    ext_uid = external_user_id or "default"

    async with get_db() as db:
        async with db.execute("SELECT id FROM oauth_brokers WHERE id=?", (broker_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"OAuth broker '{broker_id}' not found")

        async with db.execute(
            "SELECT account_id FROM oauth_broker_accounts WHERE broker_id=? AND api_host=? AND external_user_id=?",
            (broker_id, api_host, ext_uid),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, f"No connected account found for api_host='{api_host}' external_user_id='{ext_uid}'")

    account_id = row[0]
    host_slug = api_host.replace(".", "-")
    cred_id = f"pipedream-{account_id}-{host_slug}"

    # 1. Revoke upstream in Pipedream
    pipedream_revoked = False
    live_broker = next(
        (b for b in oauth_broker_registry.brokers if getattr(b, "broker_id", None) == broker_id),
        None,
    )
    if live_broker is None:
        from src.brokers.pipedream import PipedreamOAuthBroker
        brokers = await PipedreamOAuthBroker.from_db()
        live_broker = next((b for b in brokers if b.broker_id == broker_id), None)

    if live_broker is not None:
        try:
            import urllib.request as _urlreq
            import urllib.error as _urlerr
            pd_token = await live_broker._get_access_token()
            pd_url = f"https://api.pipedream.com/v1/connect/{live_broker.project_id}/accounts/{account_id}"
            req = _urlreq.Request(pd_url, method="DELETE")
            req.add_header("Authorization", f"Bearer {pd_token}")
            req.add_header("X-PD-Environment", live_broker.environment)
            try:
                with _urlreq.urlopen(req, timeout=10):
                    pass
                pipedream_revoked = True
                log.info("Pipedream account %s revoked via API", account_id)
            except _urlerr.HTTPError as http_err:
                body = http_err.read().decode("utf-8", errors="replace")
                log.warning("Failed to revoke Pipedream account %s: HTTP %s %s — body: %s — continuing with local cleanup",
                            account_id, http_err.code, http_err.reason, body)
        except Exception as exc:
            log.warning("Failed to revoke Pipedream account %s: %s — continuing with local cleanup", account_id, exc)

    # 2. Remove from toolkit provisioning
    async with get_db() as db:
        await db.execute("DELETE FROM toolkit_credentials WHERE credential_id=?", (cred_id,))
        await db.commit()

    # 3. Delete from vault
    await vault.delete_credential(cred_id)

    # 4. Delete from oauth_broker_accounts
    async with get_db() as db:
        await db.execute(
            "DELETE FROM oauth_broker_accounts WHERE broker_id=? AND api_host=? AND external_user_id=?",
            (broker_id, api_host, ext_uid),
        )
        await db.commit()

    return {
        "status": "ok",
        "broker_id": broker_id,
        "api_host": api_host,
        "account_id": account_id,
        "credential_id": cred_id,
        "pipedream_revoked": pipedream_revoked,
        "deleted": True,
    }


@router.delete(
    "/{broker_id}",
    summary="Remove an OAuth broker",
    dependencies=[Depends(require_human_session)],
)
async def delete_oauth_broker(broker_id: BrokerIdPath):
    """Remove a broker and all its connected account mappings.

    Does not revoke tokens on the provider side — do that in the provider's dashboard.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM oauth_brokers WHERE id=?", (broker_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"OAuth broker '{broker_id}' not found")
        await db.execute("DELETE FROM oauth_brokers WHERE id=?", (broker_id,))
        await db.commit()

    oauth_broker_registry.deregister(broker_id)
    log.info("OAuth broker '%s' removed", broker_id)

    return {"status": "ok", "broker_id": broker_id, "deleted": True}
