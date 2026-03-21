"""Upstream API credentials vault routes."""
import os
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from src.models import CredentialCreate, CredentialOut, CredentialPatch
import src.vault as vault
from src.db import get_db


def _self_api_id() -> str:
    return os.getenv("JENTIC_PUBLIC_HOSTNAME") or os.getenv("JENTIC_HOSTNAME") or "jentic-mini.home.seanblanchfield.com"


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


async def _api_has_native_scheme(api_id: str) -> bool:
    """True if the API's own OpenAPI spec defines at least one security scheme."""
    import json as _json
    async with get_db() as db:
        async with db.execute("SELECT spec_path FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        return False
    try:
        with open(row[0]) as f:
            spec = _json.load(f)
        schemes = spec.get("components", {}).get("securitySchemes", {})
        global_sec = spec.get("security", [])
        return bool(schemes and global_sec)
    except Exception:
        return False


@router.post("", response_model=CredentialOut, status_code=201, summary="Store an upstream API credential — add a secret to the vault for broker injection")
async def create(body: CredentialCreate, request: Request):
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "POST", "/credentials"):
            raise HTTPException(status_code=403, detail="Storing credentials requires a human session, or an agent key with an explicit POST /credentials allow rule on the jentic-mini credential.")
    """Stores an encrypted upstream API credential in the vault. Values are never returned after creation.
    Bind api_id and scheme_name to enable automatic broker injection for that API.
    Enroll in a named toolkit via POST /toolkits/{id}/credentials to scope access.
    If the API has no registered security scheme, first call POST /apis/{api_id}/scheme.
    """
    api_id = getattr(body, "api_id", None)
    scheme_name = getattr(body, "scheme_name", None)

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
        has_native = await _api_has_native_scheme(api_id)
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
                            "The scheme_name for your credential is the key used in securitySchemes "
                            "(e.g. 'ApiKeyAuth', 'BearerAuth', 'BasicAuth' from the examples above)."
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
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return cred


@router.get("/{cid}", response_model=CredentialOut, summary="Get an upstream API credential by ID")
async def get_credential(cid: str):
    """Retrieve metadata for a single credential. Value is never returned."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, label, api_id, scheme_name, created_at, updated_at FROM credentials WHERE id=?",
            (cid,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Credential not found")
    return {"id": row[0], "label": row[1], "api_id": row[2], "scheme_name": row[3],
            "created_at": row[4], "updated_at": row[5]}


@router.patch("/{cid}", response_model=CredentialOut, summary="Update an upstream API credential — rotate a secret or fix its API binding")
async def patch(cid: str, body: CredentialPatch, request: Request):
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "PATCH", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Updating credentials requires a human session, or an agent key with an explicit PATCH /credentials allow rule on the jentic-mini credential.")
    row = await vault.patch_credential(cid, body.label, body.value, body.api_id, body.scheme_name)
    if not row:
        raise HTTPException(404, "Credential not found")
    return row


@router.delete("/{cid}", status_code=204, summary="Delete an upstream API credential")
async def delete(cid: str, request: Request):
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "DELETE", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Deleting credentials requires a human session, or an agent key with an explicit DELETE /credentials allow rule on the jentic-mini credential.")
    if not await vault.delete_credential(cid):
        raise HTTPException(404, "Credential not found")


@router.get("", summary="List upstream API credentials — labels and API bindings only, no secret values", response_model=list[CredentialOut])
async def list_credentials(request: Request, api_id: str | None = None):
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
            f"SELECT c.id, c.label, c.api_id, c.scheme_name, c.created_at, c.updated_at "
            f"FROM credentials c {where} ORDER BY c.created_at DESC",
            params,
        ) as cur:
            rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "label": r[1],
            "api_id": r[2],
            "scheme_name": r[3],
            "created_at": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]
