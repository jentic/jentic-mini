"""Upstream API credentials vault routes."""
import json
import logging
import re
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.models import CredentialCreate, CredentialOut, CredentialPatch
import src.vault as vault
from src.db import get_db
from src.config import JENTIC_PUBLIC_HOSTNAME

log = logging.getLogger("jentic")


def _self_api_id() -> str:
    return JENTIC_PUBLIC_HOSTNAME


async def _agent_has_credential_write_permission(toolkit_id: str | None, method: str, path: str) -> bool:
    """Check if an agent toolkit has been explicitly granted credential write access
    via a policy rule on the internal jentic-mini credential.
    Human sessions always bypass this check (handled by the caller).
    """
    if not toolkit_id:
        return False
    cred_ids = await vault.get_credential_ids_for_route(toolkit_id, JENTIC_PUBLIC_HOSTNAME, "")
    if not cred_ids:
        return False
    from src.routers.toolkits import check_credential_policy
    for cred_id in cred_ids:
        allowed, _ = await check_credential_policy(cred_id, method=method, path=path)
        if allowed:
            return True
    return False

router = APIRouter(prefix="/credentials")


@router.post("", response_model=CredentialOut, status_code=201, summary="Store an upstream API credential — add a secret to the vault for broker injection")
async def create(body: CredentialCreate, request: Request):
    """Store an encrypted credential in the vault for automatic broker injection.

    Values are encrypted at rest and **never returned** after creation. Set `routes` to
    declare which host+path prefixes this credential covers; the broker will inject it
    automatically when proxying calls matching any route.

    ---

    ### `auth_type` reference

    Set `auth_type` to tell the broker how to inject the credential into upstream requests.

    | `auth_type` | Broker injects | When to use |
    |---|---|---|
    | `bearer` | `Authorization: Bearer {value}` | REST APIs, OAuth access tokens, JWTs |
    | `basic` | `Authorization: Basic base64({identity or 'token'}:{value})` | HTTP Basic auth, git-over-HTTPS |
    | `apiKey` | Custom header `= {value}` | API key in a named header |

    ---

    ### Workflow

    1. Post this endpoint with `routes`, `auth_type`, `value` (and `identity` if needed).
    2. The broker injects the credential automatically on every proxied call matching a route.
    3. To scope a credential to a specific toolkit: `POST /toolkits/{id}/credentials`.
    """
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "POST", "/credentials"):
            raise HTTPException(status_code=403, detail="Storing credentials requires a human session, or an agent key with an explicit POST /credentials allow rule on the jentic-mini credential.")

    try:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", body.label).strip("_").upper()
        env_var = slug or f"CRED_{uuid.uuid4().hex[:8].upper()}"
        cred = await vault.create_credential(
            body.label,
            env_var,
            body.value,
            routes=body.routes,
            auth_type=body.auth_type,
            identity=getattr(body, "identity", None),
            credential_id=body.id,
        )
    except Exception:
        log.exception("Failed to create credential")
        raise HTTPException(400, "Failed to create credential.")

    return cred


@router.get("/{cid:path}", response_model=CredentialOut, summary="Get an upstream API credential by ID")
async def get_credential(cid: str):
    """Retrieve metadata for a single credential. Value is never returned."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, label, routes, auth_type, created_at, updated_at, identity FROM credentials WHERE id=?",
            (cid,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Credential not found")
    try:
        routes = json.loads(row[2]) if row[2] else []
    except (json.JSONDecodeError, TypeError):
        routes = []
    return {"id": row[0], "label": row[1], "routes": routes, "auth_type": row[3],
            "created_at": row[4], "updated_at": row[5], "identity": row[6] if len(row) > 6 else None}


@router.patch("/{cid:path}", response_model=CredentialOut, summary="Update an upstream API credential — rotate a secret or update routes")
async def patch(cid: str, body: CredentialPatch, request: Request):
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "PATCH", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Updating credentials requires a human session, or an agent key with an explicit PATCH /credentials allow rule on the jentic-mini credential.")
    row = await vault.patch_credential(cid, body.label, body.value,
                                       routes=body.routes, auth_type=body.auth_type,
                                       identity=getattr(body, "identity", None))
    if not row:
        raise HTTPException(404, "Credential not found")
    return row


@router.delete("/{cid:path}", status_code=204, summary="Delete an upstream API credential")
async def delete(cid: str, request: Request):
    if not request.state.is_human_session:
        if not await _agent_has_credential_write_permission(request.state.toolkit_id, "DELETE", f"/credentials/{cid}"):
            raise HTTPException(status_code=403, detail="Deleting credentials requires a human session, or an agent key with an explicit DELETE /credentials allow rule on the jentic-mini credential.")
    if not await vault.delete_credential(cid):
        raise HTTPException(404, "Credential not found")


@router.get("", summary="List upstream API credentials — labels and routes only, no secret values", response_model=list[CredentialOut])
async def list_credentials(request: Request, route: str | None = None):
    """List stored upstream API credentials. Values are never returned.

    All authenticated callers (agent keys and human sessions) can see all credential
    labels and IDs — this is intentional. Labels are not secrets, and agents need
    to discover credential IDs in order to file targeted `grant` access requests.

    Filter with `?route=www.googleapis.com` to list credentials matching a host prefix.
    """
    async with get_db() as db:
        if route:
            async with db.execute(
                """SELECT id, label, routes, auth_type, created_at, updated_at, identity
                   FROM credentials
                   WHERE EXISTS (
                       SELECT 1 FROM json_each(routes)
                       WHERE value LIKE ? OR ? LIKE (value || '%')
                   )
                   ORDER BY created_at DESC""",
                (f"{route}%", route),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT id, label, routes, auth_type, created_at, updated_at, identity "
                "FROM credentials ORDER BY created_at DESC",
            ) as cur:
                rows = await cur.fetchall()

    results = []
    for r in rows:
        try:
            routes_parsed = json.loads(r[2]) if r[2] else []
        except (json.JSONDecodeError, TypeError):
            routes_parsed = []
        results.append({
            "id": r[0],
            "label": r[1],
            "routes": routes_parsed,
            "auth_type": r[3],
            "created_at": r[4],
            "updated_at": r[5],
            "identity": r[6] if len(r) > 6 else None,
        })
    return results
