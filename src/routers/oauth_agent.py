"""OAuth agent identity: RFC 8414 discovery, RFC 7591 registration, token and revoke endpoints."""

from __future__ import annotations

import base64
import json
import time
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Body, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from src.agent_identity_gate import verify_registration_access_token
from src.agent_identity_util import (
    extract_jwks_public_key_x,
    hash_token,
    new_access_token,
    new_client_id,
    new_refresh_token,
    new_registration_access_token,
    verify_jwt_bearer_assertion,
)
from src.config import (
    AGENT_ACCESS_TTL,
    AGENT_NONCE_WINDOW,
    AGENT_REFRESH_TTL,
    AGENT_REGISTRATION_TOKEN_TTL,
)
from src.db import DB_PATH, get_db
from src.utils import build_absolute_url


router = APIRouter(tags=["oauth"])


def _oauth_error(status: int, error: str, description: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": error, "error_description": description},
    )


def _jwt_payload_unverified(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("bad_jwt")
    payload_b = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b))


@router.get(
    "/.well-known/oauth-authorization-server",
    summary="OAuth 2.0 Authorization Server Metadata (RFC 8414)",
)
async def oauth_authorization_server_metadata(request: Request):
    issuer = build_absolute_url(request, "").rstrip("/")
    return {
        "issuer": issuer,
        "registration_endpoint": f"{issuer}/register",
        "token_endpoint": f"{issuer}/oauth/token",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "grant_types_supported": [
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "refresh_token",
        ],
        "token_endpoint_auth_methods_supported": ["private_key_jwt"],
        "token_endpoint_auth_signing_alg_values_supported": ["EdDSA"],
        "response_types_supported": ["none"],
    }


@router.post("/register", status_code=201, summary="Dynamic Client Registration (RFC 7591)")
async def dynamic_client_registration(request: Request, body: dict[str, Any] = Body(...)):
    """Register an agent identity (client_name + jwks). Returns pending status until a human approves."""
    client_name = (body.get("client_name") or "").strip()
    jwks = body.get("jwks")
    if not client_name:
        raise HTTPException(400, "client_name is required")
    if not isinstance(jwks, dict):
        raise HTTPException(400, "jwks must be an object")

    try:
        extract_jwks_public_key_x(jwks)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    client_id = new_client_id()
    now = time.time()
    rat = new_registration_access_token()
    rat_hash = hash_token(rat)
    rat_exp = now + AGENT_REGISTRATION_TOKEN_TTL
    registration_client_uri = build_absolute_url(request, f"/register/{client_id}")
    jwks_json = json.dumps(jwks)

    async with get_db() as db:
        await db.execute(
            """INSERT INTO agents (
                   client_id, client_name, status, jwks_json,
                   registration_token_hash, registration_token_expires_at,
                   registration_client_uri, created_at
               ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (client_id, client_name, jwks_json, rat_hash, rat_exp, registration_client_uri, now),
        )
        await db.commit()

    return {
        "client_id": client_id,
        "client_name": client_name,
        "registration_access_token": rat,
        "registration_client_uri": registration_client_uri,
        "grant_types": ["urn:ietf:params:oauth:grant-type:jwt-bearer"],
        "token_endpoint_auth_method": "private_key_jwt",
        "jwks": jwks,
        "status": "pending",
    }


@router.get("/register/{client_id}", summary="Read client registration (RFC 7592)")
async def get_registration(client_id: str, request: Request):
    auth = request.headers.get("Authorization", "")
    raw_bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else None

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT client_id, client_name, jwks_json, status, registration_client_uri,
                      deleted_at
               FROM agents WHERE client_id=?""",
            (client_id,),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, "Unknown client_id")

    if row["deleted_at"] is not None and not getattr(request.state, "is_human_session", False):
        raise HTTPException(404, "Unknown client_id")

    via_rat = False
    raw_rat: str | None = None
    if getattr(request.state, "is_human_session", False):
        pass
    elif raw_bearer and raw_bearer.startswith("rat_"):
        if not await verify_registration_access_token(client_id, raw_bearer):
            return _oauth_error(401, "invalid_token", "Invalid registration_access_token")
        via_rat = True
        raw_rat = raw_bearer
    elif raw_bearer and raw_bearer.startswith("at_"):
        if getattr(request.state, "agent_client_id", None) != client_id:
            return _oauth_error(
                401, "invalid_token", "Agent access token does not match this client_id"
            )
    else:
        return _oauth_error(401, "invalid_token", "Missing or invalid credentials")

    try:
        jwks = json.loads(row["jwks_json"])
    except Exception:
        jwks = {}

    out: dict[str, Any] = {
        "client_id": row["client_id"],
        "client_name": row["client_name"],
        "jwks": jwks,
        "grant_types": ["urn:ietf:params:oauth:grant-type:jwt-bearer"],
        "token_endpoint_auth_method": "private_key_jwt",
        "registration_client_uri": row["registration_client_uri"],
        "status": row["status"],
    }
    if via_rat and raw_rat is not None:
        out["registration_access_token"] = raw_rat
    return out


def _registration_management_unsupported() -> JSONResponse:
    # RFC 7592 §1: "the authorization server MAY return an HTTP 403 (Forbidden)
    # error code if a particular action is not supported."
    return JSONResponse(
        status_code=403,
        content={
            "error": "operation_not_supported",
            "message": "Client metadata updates and self-deregistration are not supported. "
            "Contact an administrator to rotate keys (PUT /agents/{client_id}/jwks) or "
            "deregister (DELETE /agents/{client_id}).",
        },
    )


@router.put(
    "/register/{client_id}",
    summary="Update client registration (RFC 7592, not supported)",
    include_in_schema=False,
)
async def put_registration(client_id: str):
    return _registration_management_unsupported()


@router.delete(
    "/register/{client_id}",
    summary="Delete client registration (RFC 7592, not supported)",
    include_in_schema=False,
)
async def delete_registration(client_id: str):
    return _registration_management_unsupported()


@router.post("/oauth/token", summary="OAuth 2.0 token endpoint")
async def oauth_token(
    request: Request,
    grant_type: Annotated[str | None, Form()] = None,
    assertion: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
):
    token_endpoint_aud = build_absolute_url(request, "/oauth/token")

    if grant_type == "urn:ietf:params:oauth:grant-type:jwt-bearer":
        if not assertion:
            return _oauth_error(400, "invalid_request", "assertion is required")
        try:
            payload_pre = _jwt_payload_unverified(assertion)
            iss = payload_pre.get("iss")
        except Exception:
            return _oauth_error(400, "invalid_grant", "Malformed assertion JWT")

        if not iss or not isinstance(iss, str):
            return _oauth_error(400, "invalid_grant", "assertion iss is required")

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT client_id, client_name, status, jwks_json FROM agents
                   WHERE client_id=? AND deleted_at IS NULL""",
                (iss,),
            ) as cur:
                agent = await cur.fetchone()

        if not agent:
            return _oauth_error(400, "invalid_grant", "Unknown client_id (iss)")
        if agent["status"] != "approved":
            return _oauth_error(
                400,
                "invalid_grant",
                "Client registration is not approved yet",
            )

        try:
            pub_x = extract_jwks_public_key_x(json.loads(agent["jwks_json"]))
            payload = verify_jwt_bearer_assertion(
                assertion,
                pub_x,
                expected_iss=iss,
                expected_aud=token_endpoint_aud,
            )
        except (ValueError, json.JSONDecodeError):
            return _oauth_error(
                400,
                "invalid_grant",
                "Client has no valid signing key",
            )

        jti = str(payload["jti"])
        now = time.time()
        async with get_db() as db:
            async with db.execute("SELECT jti FROM agent_nonces WHERE jti=?", (jti,)) as cur:
                if await cur.fetchone():
                    return _oauth_error(400, "invalid_grant", "jti replay")
            await db.execute(
                "INSERT INTO agent_nonces (jti, client_id, expires_at) VALUES (?,?,?)",
                (jti, iss, now + AGENT_NONCE_WINDOW),
            )
            await db.execute("DELETE FROM agent_nonces WHERE expires_at < ?", (now,))
            await db.commit()

        at = new_access_token()
        rt = new_refresh_token()
        at_h, rt_h = hash_token(at), hash_token(rt)
        exp_at = now + AGENT_ACCESS_TTL
        rt_exp = now + AGENT_REFRESH_TTL
        async with get_db() as db:
            await db.execute(
                """INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at, created_at)
                   VALUES (?, ?, 'access', ?, ?)""",
                (at_h, iss, exp_at, now),
            )
            await db.execute(
                """INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at, created_at)
                   VALUES (?, ?, 'refresh', ?, ?)""",
                (rt_h, iss, rt_exp, now),
            )
            await db.commit()

        return {
            "access_token": at,
            "token_type": "Bearer",
            "expires_in": AGENT_ACCESS_TTL,
            "refresh_token": rt,
        }

    if grant_type == "refresh_token":
        if not refresh_token or not refresh_token.startswith("rt_"):
            return _oauth_error(400, "invalid_request", "refresh_token is required")
        rt_h = hash_token(refresh_token)
        now = time.time()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT token_hash, client_id, expires_at, consumed_at
                   FROM agent_tokens WHERE token_hash=? AND token_type='refresh'""",
                (rt_h,),
            ) as cur:
                row = await cur.fetchone()

        if not row or row["consumed_at"] is not None:
            return _oauth_error(400, "invalid_grant", "Invalid or consumed refresh token")
        if row["expires_at"] < now:
            return _oauth_error(400, "invalid_grant", "Refresh token expired")

        cid = row["client_id"]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT status, jwks_json FROM agents
                   WHERE client_id=? AND deleted_at IS NULL""",
                (cid,),
            ) as cur:
                ag = await cur.fetchone()
        if not ag or ag["status"] != "approved":
            return _oauth_error(400, "invalid_grant", "Client is not active")
        try:
            extract_jwks_public_key_x(json.loads(ag["jwks_json"]))
        except (ValueError, json.JSONDecodeError):
            return _oauth_error(
                400,
                "invalid_grant",
                "Client has no valid signing key",
            )

        new_at = new_access_token()
        new_rt = new_refresh_token()
        new_at_h, new_rt_h = hash_token(new_at), hash_token(new_rt)
        exp_at = now + AGENT_ACCESS_TTL
        rt_exp = now + AGENT_REFRESH_TTL

        async with get_db() as db:
            await db.execute(
                "UPDATE agent_tokens SET consumed_at=? WHERE token_hash=?",
                (now, rt_h),
            )
            await db.execute(
                """INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at,
                       parent_token_hash, created_at)
                   VALUES (?, ?, 'access', ?, ?, ?)""",
                (new_at_h, cid, exp_at, rt_h, now),
            )
            await db.execute(
                """INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at,
                       parent_token_hash, created_at)
                   VALUES (?, ?, 'refresh', ?, ?, ?)""",
                (new_rt_h, cid, rt_exp, rt_h, now),
            )
            await db.commit()

        return {
            "access_token": new_at,
            "token_type": "Bearer",
            "expires_in": AGENT_ACCESS_TTL,
            "refresh_token": new_rt,
        }

    return _oauth_error(400, "unsupported_grant_type", f"Unknown grant_type: {grant_type!r}")


@router.post("/oauth/revoke", summary="OAuth 2.0 token revocation (RFC 7009)")
async def oauth_revoke(
    request: Request,
    token: Annotated[str | None, Form()] = None,
    token_type_hint: Annotated[str | None, Form()] = None,
):
    if not token:
        return _oauth_error(400, "invalid_request", "token is required")
    is_human = getattr(request.state, "is_human_session", False)
    caller_cid = getattr(request.state, "agent_client_id", None)
    # Toolkit keys (tk_…) cannot revoke OAuth tokens — RFC 7009 implies the client
    # that holds the token. Require an agent access token (at_…) or human session.
    if not is_human and caller_cid is None:
        return _oauth_error(403, "unauthorized_client", "Toolkit keys cannot revoke OAuth tokens")
    th = hash_token(token)
    async with get_db() as db:
        if not is_human:
            async with db.execute(
                "SELECT client_id FROM agent_tokens WHERE token_hash=?", (th,)
            ) as cur:
                row = await cur.fetchone()
            # RFC 7009: revocation of an unknown token is treated as success.
            if row is None:
                return Response(status_code=200)
            if row["client_id"] != caller_cid:
                return _oauth_error(
                    403, "unauthorized_client", "Cannot revoke another client's token"
                )
        await db.execute("DELETE FROM agent_tokens WHERE token_hash=?", (th,))
        await db.commit()
    return Response(status_code=200)
