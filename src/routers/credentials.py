"""Upstream API credentials vault routes."""
import json
import logging
import uuid
from typing import Annotated

import yaml
from fastapi import APIRouter, Body, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from src.models import CredentialCreate, CredentialOut, CredentialPatch
import src.vault as vault
from src.db import get_db
from src.auth import client_ip
from src.config import JENTIC_PUBLIC_HOSTNAME

log = logging.getLogger("jentic")
audit_log = logging.getLogger("jentic.audit")


def _self_api_id() -> str:
    return JENTIC_PUBLIC_HOSTNAME


async def _agent_has_credential_write_permission(toolkit_id: str | None, method: str, path: str) -> bool:
    """Check if an agent toolkit has been explicitly granted credential write access
    via a policy rule on the internal jentic-mini credential.
    Human sessions always bypass this check (handled by the caller).
    """
    if not toolkit_id:
        return False
    cred_ids = await vault.get_credential_ids_for_api(toolkit_id, _self_api_id())
    if not cred_ids:
        return False
    from src.routers.toolkits import check_credential_policy
    for cred_id in cred_ids:
        allowed, _ = await check_credential_policy(cred_id, method=method, path=path)
        if allowed:
            return True
    return False

router = APIRouter(prefix="/credentials")


async def _get_confirmed_scheme(api_id: str, scheme_name: str | None) -> dict | None:
    """
    Return the confirmed overlay row for (api_id, scheme_name), or None.
    If scheme_name is None, returns the first confirmed overlay for the API.
    """
    async with get_db() as db:
        if scheme_name:
            async with db.execute(
                """SELECT id, overlay FROM api_overlays
                   WHERE api_id=? AND status='confirmed'
                   AND json_extract(overlay, '$.actions[0].update.components.securitySchemes."' || ? || '"') IS NOT NULL
                   LIMIT 1""",
                (api_id, scheme_name),
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute(
                "SELECT id, overlay FROM api_overlays WHERE api_id=? AND status='confirmed' LIMIT 1",
                (api_id,),
            ) as cur:
                row = await cur.fetchone()
    return row


async def api_has_native_scheme(api_id: str) -> bool:
    """True if the API's own OpenAPI spec defines at least one security scheme."""
    async with get_db() as db:
        async with db.execute("SELECT spec_path FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        return False
    try:
        with open(row[0]) as f:
            raw = f.read()
        if row[0].endswith((".yaml", ".yml")):
            spec = yaml.safe_load(raw)
        else:
            try:
                spec = json.loads(raw)
            except json.JSONDecodeError:
                spec = yaml.safe_load(raw)
        schemes = spec.get("components", {}).get("securitySchemes", {})
        return bool(schemes)
    except Exception:
        return False


@router.post(
    "",
    response_model=CredentialOut,
    status_code=201,
    summary="Store an upstream API credential — add a secret to the vault for broker injection",
    openapi_extra={"requestBody": {"description": "Credential details: label for identification, encrypted value (API key/token/password), optional identity (username/client ID), API ID, and auth type"}},
)
async def create(body: CredentialCreate, request: Request):
    """Store an encrypted credential in the vault for automatic broker injection.

    Values are encrypted at rest and **never returned** after creation. Set `api_id` to
    bind the credential to an API; the broker will inject it automatically when proxying
    calls to that API.

    ---

    ### `auth_type` reference

    Set `auth_type` to tell the broker how to inject the credential into upstream requests.
    Based on the [Postman auth type taxonomy](https://learning.postman.com/docs/sending-requests/authorization/authorization-types/).

    | `auth_type` | Status | Broker injects | `value` | `identity` |
    |---|---|---|---|---|
    | `bearer` | ✅ implemented | `Authorization: Bearer {value}` | Token, PAT, or OAuth access token | Not used |
    | `basic` | ✅ implemented | `Authorization: Basic base64({identity or "token"}:{value})` | Password or PAT | Username (optional — defaults to `"token"` if omitted, works for GitHub PATs) |
    | `apiKey` | ✅ implemented | Custom header or query param `= {value}` | API key | For **compound schemes** (e.g. Discourse `Api-Key` + `Api-Username`): set `identity` to the username — one credential covers both headers when the overlay uses canonical `Secret`/`Identity` scheme names |
    | `oauth2` | ⚠️ partial | `Authorization: Bearer {value}` — token must be pre-obtained | Access token (Pipedream-managed flows only via `pipedream_oauth`) | Not used |
    | `digest` | 🔲 planned | RFC 2617 challenge-response (nonce/HMAC handshake) | Password | Username |
    | `jwt` | 🔲 planned | `Authorization: Bearer {signed_jwt}` — auto-generated from signing key | Private key or secret | Key ID (`kid`) — signing algorithm and claims go in `context` |
    | `aws_sig4` | 🔲 planned | `Authorization: AWS4-HMAC-SHA256 ...` signed headers | AWS Secret Access Key | AWS Access Key ID — region and service go in `context` |
    | `oauth1` | 🔲 planned | HMAC-SHA1 signed request (nonce + timestamp) | OAuth secret | OAuth consumer key |
    | `hawk` | 🔲 planned | `Authorization: Hawk ...` HMAC request signing | Hawk secret | Hawk key ID |
    | `ntlm` | 🔲 not planned | Windows NTLM challenge-response | Password | Username + domain |
    | `akamai_edgegrid` | 🔲 not planned | Akamai EdgeGrid signing | Client secret | Client token + access token in `context` |

    **Notes:**
    - `pipedream_oauth` is a reserved value written by the Pipedream integration — do not set it manually.
    - For `oauth2` full flows (auth code, client credentials, PKCE, token refresh) see the roadmap.
    - `context` (not yet exposed) will hold auxiliary fields for multi-value schemes (JWT claims, AWS region/service, etc.).

    ---

    ### Workflow

    1. Call `GET /apis/{api_id}` — check `security_schemes` and `credentials_configured` to find gaps.
    2. Post this endpoint with `api_id`, `auth_type`, `value` (and `identity` if needed).
    3. The broker injects the credential automatically on every proxied call to that API.
    4. To scope a credential to a specific toolkit: `POST /toolkits/{id}/credentials`.

    If the API has no registered security scheme yet, submit an overlay first: `POST /apis/{api_id}/overlays`.
    """
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "POST", "/credentials"):
            raise HTTPException(status_code=403, detail="Storing credentials requires a human session, or an agent key with an explicit POST /credentials allow rule on the jentic-mini credential.")
    api_id = getattr(body, "api_id", None)
    scheme_name = getattr(body, "auth_type", None)

    if api_id:
        # ── Lazy import: if api_id is a catalog API not yet locally registered, import it now ──
        from src.routers.catalog import ensure_catalog_api_imported, lazy_import_catalog_workflows
        resolved_id = await ensure_catalog_api_imported(api_id)
        if resolved_id and resolved_id != api_id:
            # Import changed the api_id (e.g. 'discord.com' → 'discord.com/api')
            api_id = resolved_id
            body = body.model_copy(update={"api_id": api_id})

        # Also import associated catalog workflows (fire-and-forget on error)
        try:
            await lazy_import_catalog_workflows(api_id)
        except Exception as _wf_err:
            log.warning("Workflow auto-import failed for '%s' (non-fatal): %s", api_id, _wf_err)

        # Check native spec first
        has_native = await api_has_native_scheme(api_id)
        if not has_native:
            # Check for any overlay (pending OR confirmed) — pending is enough to proceed.
            # The first successful broker call will confirm it. This is intentional bootstrap flow:
            # overlay submitted → credential added → broker call → overlay confirmed.
            async with get_db() as db:
                async with db.execute(
                    "SELECT id FROM api_overlays WHERE api_id=? LIMIT 1",
                    (api_id,),
                ) as cur:
                    any_overlay = await cur.fetchone()
            if not any_overlay:
                # No overlay at all — instruct the agent to contribute one
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": "no_security_scheme",
                        "api_id": api_id,
                        "message": (
                            f"No security scheme is on record for '{api_id}'. "
                            f"Before adding a credential, submit an overlay that declares the scheme."
                        ),
                        "instructions": (
                            f"Research how '{api_id}' authenticates requests, then submit an "
                            f"OpenAPI Overlay 1.0 document to POST /apis/{api_id}/overlays. "
                            f"Once submitted, retry POST /credentials."
                        ),
                        "submit_to": f"POST /apis/{api_id}/overlays",
                        "examples": {
                            "api_key_in_header": {
                                "overlay": "1.0.0",
                                "info": {"title": f"{api_id} auth", "version": "1.0.0"},
                                "actions": [{"target": "$", "update": {"components": {"securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Your-Header-Name"}}}}}],
                            },
                            "bearer_token": {
                                "overlay": "1.0.0",
                                "info": {"title": f"{api_id} auth", "version": "1.0.0"},
                                "actions": [{"target": "$", "update": {"components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}}}}],
                            },
                            "basic_auth": {
                                "overlay": "1.0.0",
                                "info": {"title": f"{api_id} auth", "version": "1.0.0"},
                                "actions": [{"target": "$", "update": {"components": {"securitySchemes": {"BasicAuth": {"type": "http", "scheme": "basic"}}}}}],
                            },
                        },
                        "note": (
                            "Set auth_type on the credential to 'bearer', 'basic', or 'apiKey' — "
                            "the broker uses this to match the right security scheme from the spec."
                        ),
                    },
                )

    try:
        # Auto-generate a stable internal slug (not exposed via API)
        import re
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{body.api_id or ''}_{body.label}").strip("_").upper()
        env_var = slug or f"CRED_{uuid.uuid4().hex[:8].upper()}"
        cred = await vault.create_credential(
            body.label,
            env_var,
            body.value,
            api_id=api_id,
            scheme_name=scheme_name,
            identity=getattr(body, "identity", None),
        )
    except Exception as e:
        log.exception("Failed to create credential")
        raise HTTPException(400, "Failed to create credential.")

    actor = "human" if request.state.is_human_session else f"toolkit={request.state.toolkit_id}"
    audit_log.info("CREDENTIAL_CREATED id=%s label=%s api_id=%s actor=%s ip=%s", cred["id"], cred["label"], api_id, actor, client_ip(request))
    return cred


@router.get("/{cid:path}", response_model=CredentialOut, summary="Get an upstream API credential by ID")
async def get_credential(cid: Annotated[str, Path(description="Credential ID (format: hostname or hostname/path)")]):
    """Retrieve metadata for a single credential.

    Returns the credential's label, API binding, auth type, and identity field (if set).
    The secret value is never returned after creation for security.

    Parameters:
        cid: Credential ID (format: hostname or hostname/path, e.g. 'api.github.com')

    Returns:
        Credential metadata including id, label, api_id, auth_type, timestamps, and identity.

    Use this to confirm a credential exists before binding it to a toolkit or to inspect
    its configuration before making authenticated calls.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT id, label, api_id, auth_type, created_at, updated_at, identity FROM credentials WHERE id=?",
            (cid,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Credential not found")
    return {"id": row[0], "label": row[1], "api_id": row[2], "auth_type": row[3],
            "created_at": row[4], "updated_at": row[5], "identity": row[6] if len(row) > 6 else None}


@router.patch(
    "/{cid:path}",
    response_model=CredentialOut,
    summary="Update an upstream API credential — rotate a secret or fix its API binding",
    openapi_extra={"requestBody": {"description": "Fields to update: label, value (for rotation), identity, api_id, or auth_type — only provided fields are changed"}},
)
async def patch(
    cid: Annotated[str, Path(description="Credential ID to update")],
    body: CredentialPatch,
    request: Request,
):
    """
    Update a credential's label, secret value, identity field, API binding, or auth_type.

    Common use cases:
    - Rotate an expired token or password (update `value`)
    - Fix incorrect API binding (update `api_id`)
    - Add username to existing credential (update `identity`)
    - Relabel for clarity (update `label`)

    Only changed fields need to be included in the request body. Omitted fields are left unchanged.

    **Auth:** Requires human session OR agent key with explicit `PATCH /credentials` allow rule on jentic-mini credential.
    """
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "PATCH", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Updating credentials requires a human session, or an agent key with an explicit PATCH /credentials allow rule on the jentic-mini credential.")
    row = await vault.patch_credential(cid, body.label, body.value, body.api_id, body.auth_type,
                                       identity=getattr(body, "identity", None))
    if not row:
        raise HTTPException(404, "Credential not found")
    actor = "human" if request.state.is_human_session else f"toolkit={request.state.toolkit_id}"
    audit_log.info("CREDENTIAL_UPDATED id=%s actor=%s ip=%s", cid, actor, client_ip(request))
    return row


@router.delete("/{cid:path}", status_code=204, summary="Delete an upstream API credential")
async def delete(cid: Annotated[str, Path(description="Credential ID to delete")], request: Request):
    """
    Permanently delete a credential.

    The credential is removed from the vault and unbound from all toolkits that reference it.
    Agents using toolkits with this credential will immediately lose access to the upstream API.

    **Auth:** Requires human session OR agent key with explicit `DELETE /credentials` allow rule on jentic-mini credential.

    **Warning:** This operation cannot be undone. The secret value is irrecoverably destroyed.
    """
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "DELETE", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Deleting credentials requires a human session, or an agent key with an explicit DELETE /credentials allow rule on the jentic-mini credential.")
    if not await vault.delete_credential(cid):
        raise HTTPException(404, "Credential not found")
    actor = "human" if request.state.is_human_session else f"toolkit={request.state.toolkit_id}"
    audit_log.info("CREDENTIAL_DELETED id=%s actor=%s ip=%s", cid, actor, client_ip(request))


@router.get("", summary="List upstream API credentials — labels and API bindings only, no secret values", response_model=list[CredentialOut])
async def list_credentials(request: Request, api_id: Annotated[str | None, Query(description="Filter credentials by API ID (hostname)")] = None):
    """List stored upstream API credentials. Values are never returned.

    All authenticated callers (agent keys and human sessions) can see all credential
    labels and IDs — this is intentional. Labels are not secrets, and agents need
    to discover credential IDs in order to file targeted `grant` access requests
    (e.g. "bind Work Gmail" vs "bind Personal Gmail").

    Use `GET /credentials/{id}` to retrieve a specific credential by ID.
    Filter with `?api_id=api.github.com` to list all credentials for a given API.
    """

    conditions = []
    params: list = []

    if api_id:
        conditions.append("c.api_id = ?")
        params.append(api_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with get_db() as db:
        async with db.execute(
            f"SELECT c.id, c.label, c.api_id, c.auth_type, c.created_at, c.updated_at, c.identity, "
            f"       oba.account_id, oba.app_slug, oba.synced_at "
            f"FROM credentials c "
            f"LEFT JOIN oauth_broker_accounts oba ON oba.broker_id || '-' || oba.account_id || '-' || replace(oba.api_host, '.', '-') = c.id "
            f"{where} ORDER BY c.created_at DESC",
            params,
        ) as cur:
            rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "label": r[1],
            "api_id": r[2],
            "auth_type": r[3],
            "created_at": r[4],
            "updated_at": r[5],
            "identity": r[6] if len(r) > 6 else None,
            "account_id": r[7] if len(r) > 7 else None,
            "app_slug": r[8] if len(r) > 8 else None,
            "synced_at": r[9] if len(r) > 9 else None,
        }
        for r in rows
    ]
