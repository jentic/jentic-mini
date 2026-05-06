"""OAuth agent identity: RFC 8414 discovery, RFC 7591 registration, token and revoke endpoints."""

from __future__ import annotations

import base64
import json
import time
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Body, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.responses import Response

from src.agent_identity_gate import verify_registration_access_token
from src.agent_identity_util import (
    extract_jwks_public_key_x,
    hash_token,
    new_access_token,
    new_client_id,
    new_refresh_token,
    new_registration_access_token,
    sanitise_jwks,
    verify_jwt_bearer_assertion,
)
from src.config import (
    AGENT_ACCESS_TTL,
    AGENT_NONCE_WINDOW,
    AGENT_REFRESH_TTL,
    AGENT_REGISTRATION_TOKEN_TTL,
)
from src.db import DB_PATH, get_db
from src.utils import build_canonical_url


router = APIRouter(tags=["oauth"])


class OAuthError(BaseModel):
    """RFC 6749 §5.2 / RFC 7591 §3.2.2 error response body.

    OAuth routes intentionally bypass FastAPI's HTTPException → ``{"detail": ...}``
    convention so the wire shape matches the spec.
    """

    error: str = Field(description="OAuth error code (e.g. 'invalid_grant').")
    error_description: str | None = Field(
        default=None,
        description="Human-readable description; safe to log, not safe to display.",
    )


class HTTPErrorDetail(BaseModel):
    """Standard FastAPI HTTPException body — ``{"detail": "..."}``."""

    detail: str


# Response declarations reused across OAuth routes. Without these FastAPI's
# generated schema only declares 200/422, and downstream SDKs / contract tests
# treat the documented error path as "untyped" — agents see ``any`` for what
# is in fact a stable RFC-shaped object.
_OAUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": OAuthError,
        "description": "OAuth-formatted error (invalid_request, invalid_grant, unsupported_grant_type).",
    },
    401: {
        "model": OAuthError,
        "description": "OAuth-formatted authentication error (invalid_token).",
    },
}

_HTTP_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": HTTPErrorDetail, "description": "Bad request (e.g. malformed jwks)."},
    401: {"model": HTTPErrorDetail, "description": "Authentication required."},
    403: {"model": HTTPErrorDetail, "description": "Operation not permitted for this principal."},
    404: {"model": HTTPErrorDetail, "description": "Resource not found."},
}


def _oauth_error(status: int, error: str, description: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": error, "error_description": description},
    )


async def _revoke_token_family(seed_hash: str) -> None:
    """Revoke every token in the same lineage as ``seed_hash``.

    Implements RFC 6749 Security BCP §4.14: when a refresh token is presented
    after it has already been consumed, the chain is treated as compromised
    and every access/refresh token sharing the same family root (ancestor with
    ``parent_token_hash IS NULL``) is deleted in one shot. SQLite's recursive
    CTEs walk both directions: up to the root, then down to every descendant.
    """
    async with get_db() as db:
        await db.execute(
            """
            WITH RECURSIVE
              ancestors(token_hash, parent_token_hash) AS (
                SELECT token_hash, parent_token_hash
                  FROM agent_tokens WHERE token_hash = ?
                UNION ALL
                SELECT t.token_hash, t.parent_token_hash
                  FROM agent_tokens t JOIN ancestors a ON a.parent_token_hash = t.token_hash
              ),
              root AS (
                SELECT token_hash FROM ancestors WHERE parent_token_hash IS NULL LIMIT 1
              ),
              family(token_hash) AS (
                SELECT token_hash FROM root
                UNION ALL
                SELECT t.token_hash
                  FROM agent_tokens t JOIN family f ON t.parent_token_hash = f.token_hash
              )
            DELETE FROM agent_tokens WHERE token_hash IN (SELECT token_hash FROM family)
            """,
            (seed_hash,),
        )
        await db.commit()


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
    issuer = build_canonical_url(request, "").rstrip("/")
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


@router.post(
    "/register",
    status_code=201,
    summary="Dynamic Client Registration (RFC 7591)",
    responses={400: _HTTP_ERROR_RESPONSES[400]},
)
async def dynamic_client_registration(request: Request, body: dict[str, Any] = Body(...)):
    """Register an agent identity (client_name + jwks). Returns pending status until a human approves."""
    client_name = (body.get("client_name") or "").strip()
    jwks = body.get("jwks")
    if not client_name:
        raise HTTPException(400, "client_name is required")
    if not isinstance(jwks, dict):
        raise HTTPException(400, "jwks must be an object")

    try:
        cleaned_jwks = sanitise_jwks(jwks)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    client_id = new_client_id()
    now = time.time()
    rat = new_registration_access_token()
    rat_hash = hash_token(rat)
    rat_exp = now + AGENT_REGISTRATION_TOKEN_TTL
    registration_client_uri = build_canonical_url(request, f"/register/{client_id}")
    jwks_json = json.dumps(cleaned_jwks)

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
        "jwks": cleaned_jwks,
        "status": "pending",
    }


@router.get(
    "/register/{client_id}",
    summary="Read client registration (RFC 7592)",
    responses={
        401: _OAUTH_ERROR_RESPONSES[401],
        404: _HTTP_ERROR_RESPONSES[404],
    },
)
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


@router.post(
    "/oauth/token",
    summary="OAuth 2.0 token endpoint",
    responses=_OAUTH_ERROR_RESPONSES,
)
async def oauth_token(
    request: Request,
    grant_type: Annotated[str | None, Form()] = None,
    assertion: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
):
    token_endpoint_aud = build_canonical_url(request, "/oauth/token")

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

        # Uniform error for any client-bound failure to avoid an enumeration oracle:
        # unknown iss, not-yet-approved, missing key, bad signature, replayed jti, etc.
        # all collapse to the same response. The specifics are still logged server-side.
        invalid_assertion = _oauth_error(400, "invalid_grant", "Assertion is invalid")

        if not agent or agent["status"] != "approved":
            return invalid_assertion

        try:
            pub_x = extract_jwks_public_key_x(json.loads(agent["jwks_json"]))
            payload = verify_jwt_bearer_assertion(
                assertion,
                pub_x,
                expected_iss=iss,
                expected_aud=token_endpoint_aud,
            )
        except (ValueError, json.JSONDecodeError):
            return invalid_assertion

        jti = str(payload["jti"])
        now = time.time()
        at = new_access_token()
        rt = new_refresh_token()
        at_h, rt_h = hash_token(at), hash_token(rt)
        exp_at = now + AGENT_ACCESS_TTL
        rt_exp = now + AGENT_REFRESH_TTL

        # One transaction covers the jti reservation and the token mint so a crash
        # mid-flight can't consume the nonce without issuing a token (and vice
        # versa). INSERT OR IGNORE + cursor.rowcount is the atomic
        # check-and-insert that closes the read-then-write replay race.
        async with get_db() as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur = await db.execute(
                    "INSERT OR IGNORE INTO agent_nonces (jti, client_id, expires_at) "
                    "VALUES (?,?,?)",
                    (jti, iss, now + AGENT_NONCE_WINDOW),
                )
                if cur.rowcount == 0:
                    await db.rollback()
                    return invalid_assertion
                await db.execute(
                    "INSERT INTO agent_tokens (token_hash, client_id, token_type, "
                    "expires_at, created_at) VALUES (?, ?, 'access', ?, ?)",
                    (at_h, iss, exp_at, now),
                )
                await db.execute(
                    "INSERT INTO agent_tokens (token_hash, client_id, token_type, "
                    "expires_at, created_at) VALUES (?, ?, 'refresh', ?, ?)",
                    (rt_h, iss, rt_exp, now),
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                # Defence-in-depth — should be unreachable given the IGNORE above.
                await db.rollback()
                return invalid_assertion

        # Best-effort housekeeping outside the mint transaction so a busy nonce
        # table can't stall token issuance.
        async with get_db() as db:
            await db.execute("DELETE FROM agent_nonces WHERE expires_at < ?", (now,))
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

        # Uniform error for any client-bound failure — same rationale as the
        # JWT-bearer branch above (no enumeration oracle on client state).
        invalid_refresh = _oauth_error(400, "invalid_grant", "Refresh token cannot be used")

        new_at = new_access_token()
        new_rt = new_refresh_token()
        new_at_h, new_rt_h = hash_token(new_at), hash_token(new_rt)
        exp_at = now + AGENT_ACCESS_TTL
        rt_exp = now + AGENT_REFRESH_TTL

        family_compromise = False
        try:
            # Single transaction: read row, CAS-consume, validate agent, insert
            # rotated pair. Two concurrent rotations both reach the UPDATE — only
            # the one matching `consumed_at IS NULL` mutates a row (rowcount==1);
            # the loser sees rowcount==0 and falls through to invalid_grant.
            async with get_db() as db:
                db.row_factory = aiosqlite.Row
                await db.execute("BEGIN IMMEDIATE")
                try:
                    async with db.execute(
                        """SELECT token_hash, client_id, expires_at, consumed_at
                           FROM agent_tokens
                           WHERE token_hash=? AND token_type='refresh'""",
                        (rt_h,),
                    ) as cur:
                        row = await cur.fetchone()

                    if not row:
                        await db.rollback()
                        return _oauth_error(
                            400, "invalid_grant", "Invalid or consumed refresh token"
                        )
                    if row["consumed_at"] is not None:
                        # RFC 6749 BCP §4.14: refresh-token reuse signals a likely
                        # chain compromise. Defer the family-revocation sweep to
                        # outside this transaction so we can surface the rejection
                        # immediately and do the cleanup with its own commit.
                        await db.rollback()
                        family_compromise = True
                    elif row["expires_at"] < now:
                        await db.rollback()
                        return _oauth_error(400, "invalid_grant", "Refresh token expired")
                    else:
                        cid = row["client_id"]
                        async with db.execute(
                            """SELECT status, jwks_json FROM agents
                               WHERE client_id=? AND deleted_at IS NULL""",
                            (cid,),
                        ) as cur:
                            ag = await cur.fetchone()
                        if not ag or ag["status"] != "approved":
                            await db.rollback()
                            return invalid_refresh
                        try:
                            extract_jwks_public_key_x(json.loads(ag["jwks_json"]))
                        except (ValueError, json.JSONDecodeError):
                            await db.rollback()
                            return invalid_refresh

                        consume = await db.execute(
                            "UPDATE agent_tokens SET consumed_at=? "
                            "WHERE token_hash=? AND token_type='refresh' "
                            "AND consumed_at IS NULL",
                            (now, rt_h),
                        )
                        if consume.rowcount != 1:
                            # Lost the rotation race — peer transaction already
                            # consumed this row.
                            await db.rollback()
                            return invalid_refresh

                        await db.execute(
                            """INSERT INTO agent_tokens (token_hash, client_id, token_type,
                                   expires_at, parent_token_hash, created_at)
                               VALUES (?, ?, 'access', ?, ?, ?)""",
                            (new_at_h, cid, exp_at, rt_h, now),
                        )
                        await db.execute(
                            """INSERT INTO agent_tokens (token_hash, client_id, token_type,
                                   expires_at, parent_token_hash, created_at)
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
                except aiosqlite.IntegrityError:
                    # Hit the partial unique index on (parent_token_hash,
                    # token_type) — a concurrent rotation already minted from this
                    # parent. Treat as a lost race rather than a 500.
                    await db.rollback()
                    return invalid_refresh
        finally:
            if family_compromise:
                await _revoke_token_family(rt_h)

        return _oauth_error(400, "invalid_grant", "Invalid or consumed refresh token")

    return _oauth_error(400, "unsupported_grant_type", f"Unknown grant_type: {grant_type!r}")


@router.post(
    "/oauth/revoke",
    summary="OAuth 2.0 token revocation (RFC 7009)",
    responses={
        400: _OAUTH_ERROR_RESPONSES[400],
        403: {
            "model": OAuthError,
            "description": "Caller is not allowed to revoke this token (e.g. tk_ key, "
            "or at_ for a different client_id).",
        },
    },
)
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
            # row is a tuple — get_db() does not install Row factory.
            if row[0] != caller_cid:
                return _oauth_error(
                    403, "unauthorized_client", "Cannot revoke another client's token"
                )
        await db.execute("DELETE FROM agent_tokens WHERE token_hash=?", (th,))
        await db.commit()
    return Response(status_code=200)
