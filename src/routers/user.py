"""User account management — create, login, logout.

Single root account per instance. No multi-user, no roles.

Endpoints:
  POST /user/create  — create root account (one-time, 410 after first call)
  POST /user/login   — username + password → httpOnly JWT cookie
  POST /user/token   — OAuth2 password grant → Bearer JWT (for Swagger UI Authorize dialog)
  POST /user/logout  — clears session cookie (human session required)

Password reset is CLI-only:
  docker exec -it jentic-mini python3 -m src reset-password
"""

import logging
import uuid
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator

from src.auth import JWT_TTL_SECONDS, MIN_PASSWORD_LENGTH, client_ip, make_jwt
from src.db import get_db, set_setting, setup_state
from src.models import UserOut
from src.validators import validate_relative_redirect


audit_log = logging.getLogger("jentic.audit")
router = APIRouter(prefix="/user", tags=["user"])


# ── Models ────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Request body for creating the root admin account. One-time only — POST /user/create returns 410 after first use."""

    username: str = Field(description="Admin account username (will be trimmed of whitespace)")
    password: str = Field(description="Admin account password (stored as bcrypt hash)")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v):
        return v.strip() if isinstance(v, str) else v


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v):
        return v.strip() if isinstance(v, str) else v


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/create",
    status_code=201,
    summary="Create the root admin account (one-time setup)",
    openapi_extra={
        "requestBody": {
            "description": "Account credentials: username (trimmed of whitespace) and password (stored as bcrypt hash) for the root admin"
        }
    },
)
async def create_user(body: UserCreate, request: Request, response: Response):
    """Create the single root account for this instance.

    This endpoint is available **once only**. After the first call it returns
    `410 Gone`. There is no multi-user system — one human owns this instance.

    Requires `bcrypt` installed (bundled in Docker image).
    """
    # One-time guard
    state = await setup_state()
    if state["account_created"]:
        raise HTTPException(
            410,
            detail={
                "error": "account_exists",
                "message": "An admin account already exists. This endpoint is one-time only.",
                "hint": "Log in at POST /user/login.",
            },
        )

    if not body.username or not body.password:
        raise HTTPException(400, "username and password are required.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())

    async with get_db() as db:
        await db.execute(
            "INSERT INTO users (id, username, password_hash, created_via) VALUES (?, ?, ?, 'local')",
            (user_id, body.username.strip(), pw_hash),
        )
        await db.commit()

    await set_setting("account_created", "1")

    # Auto-login — issue session cookie immediately
    jwt_secret = state["jwt_secret"]
    token = make_jwt(jwt_secret)
    response.set_cookie(
        "jentic_session",
        token,
        httponly=True,
        samesite="strict",
        max_age=JWT_TTL_SECONDS,
        path=request.scope.get("root_path") or "/",
    )

    audit_log.info("ACCOUNT_CREATED user=%s ip=%s", body.username.strip(), client_ip(request))

    return {
        "message": "Admin account created. You are now logged in.",
        "username": body.username.strip(),
        "next": "You can now manage toolkits, credentials, and approve access requests.",
    }


@router.post(
    "/login",
    summary="Log in and receive a session cookie",
    openapi_extra={
        "requestBody": {
            "description": "Login credentials: username and password for the root admin account",
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["username", "password"],
                        "properties": {
                            "username": {"type": "string", "example": "admin"},
                            "password": {"type": "string", "format": "password"},
                        },
                    }
                }
            },
        }
    },
)
async def login(
    request: Request,
    response: Response,
    redirect_to: Annotated[
        str | None, Query(description="Redirect URL after successful login (relative path only)")
    ] = None,
):
    """Authenticate with username and password.

    Accepts JSON body (`{"username": ..., "password": ...}`) or HTML form data.
    Returns an httpOnly JWT session cookie valid for 30 days (sliding window).

    Pass `?redirect_to=/docs` to redirect after a successful browser form login.
    """
    ct = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
    else:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(400, "Invalid request body.")
        username = data.get("username", "")
        password = data.get("password", "")

    if not username or not password:
        raise HTTPException(400, "username and password are required.")

    async with get_db() as db:
        db.row_factory = __import__("aiosqlite").Row
        async with db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ) as cur:
            row = await cur.fetchone()

    ip = client_ip(request)
    if (
        not row
        or row["password_hash"] is None
        or not bcrypt.checkpw(password.encode(), row["password_hash"].encode())
    ):
        audit_log.warning("LOGIN_FAILED user=%s ip=%s", username.strip(), ip)
        raise HTTPException(
            401,
            detail={
                "error": "invalid_credentials",
                "message": "Username or password incorrect.",
            },
        )

    audit_log.info("LOGIN_SUCCESS user=%s ip=%s", username.strip(), ip)
    state = await setup_state()
    token = make_jwt(state["jwt_secret"])

    if redirect_to:
        safe_redirect = validate_relative_redirect(redirect_to)
        if safe_redirect is None:
            # Format both user-controlled fields with %r so repr() escapes
            # any embedded control characters — keeps this new audit line
            # injection-safe even though the validator already rejects
            # control chars in redirect_to. Truncate to bound log volume
            # under sustained probe traffic.
            audit_log.warning(
                "LOGIN_REDIRECT_BLOCKED user=%r ip=%s redirect_to=%r",
                username.strip(),
                ip,
                redirect_to[:200],
            )
            safe_redirect = "/"
        redir = RedirectResponse(url=safe_redirect, status_code=303)
        redir.set_cookie(
            "jentic_session",
            token,
            httponly=True,
            samesite="strict",
            max_age=JWT_TTL_SECONDS,
            path=request.scope.get("root_path") or "/",
        )
        return redir

    response.set_cookie(
        "jentic_session",
        token,
        httponly=True,
        samesite="strict",
        max_age=JWT_TTL_SECONDS,
        path=request.scope.get("root_path") or "/",
    )

    return {"message": "Logged in.", "username": row["username"]}


@router.post(
    "/token",
    summary="OAuth2 password grant — returns Bearer JWT",
    response_description="Access token for use in Authorization: Bearer header",
    openapi_extra={
        "requestBody": {
            "description": "OAuth2 password grant form: username, password, and grant_type='password' (form-urlencoded format)"
        }
    },
)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 password grant endpoint.

    Swagger UI's **Authorize** dialog uses this automatically when you fill in
    the *HumanLogin* username + password fields. Returns a Bearer JWT that
    Swagger UI injects as `Authorization: Bearer ...` on all subsequent calls.

    This is functionally equivalent to `POST /user/login` but returns the token
    in the response body rather than as a cookie — the standard OAuth2 pattern
    expected by Swagger UI.
    """
    username = form_data.username
    password = form_data.password

    async with get_db() as db:
        db.row_factory = __import__("aiosqlite").Row
        async with db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ) as cur:
            row = await cur.fetchone()

    if (
        not row
        or row["password_hash"] is None
        or not bcrypt.checkpw(password.encode(), row["password_hash"].encode())
    ):
        raise HTTPException(
            401,
            detail={
                "error": "invalid_client",
                "error_description": "Username or password incorrect.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    state = await setup_state()
    access_token = make_jwt(state["jwt_secret"])

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_TTL_SECONDS,
    }


@router.post(
    "/logout",
    summary="Log out — clear the session cookie",
)
async def logout(request: Request, response: Response):
    """Terminate the current human session.

    Clears the `jentic_session` httpOnly cookie if present. If you authenticated
    via Bearer token (Swagger UI OAuth2 flow), discard the token on your end —
    there is no server-side token store to invalidate.
    """
    if not getattr(request.state, "is_human_session", False):
        raise HTTPException(401, "Not logged in.")
    username = "unknown"
    try:
        async with get_db() as db:
            async with db.execute("SELECT username FROM users LIMIT 1") as cur:
                row = await cur.fetchone()
        if row:
            username = row[0]
    except Exception:
        pass
    audit_log.info("LOGOUT user=%s ip=%s", username, client_ip(request))
    response.delete_cookie("jentic_session", path=request.scope.get("root_path") or "/")
    return {"message": "Logged out."}


@router.get(
    "/me",
    summary="Check current session status",
    response_model=UserOut,
)
async def me(request: Request):
    """Returns current session info and authentication context.

    Response varies based on authentication method:
    - Human session (JWT cookie): logged_in=true, includes username
    - Trusted subnet (no auth): logged_in=false, admin=true (note about logging in for named session)
    - Agent key (X-Jentic-API-Key): logged_in=false, agent_key=true, includes toolkit_id
    - No auth: logged_in=false, agent_key=false

    Useful for UI to determine what features to show and whether to require login.
    Agents can call this to confirm their key is valid and see which toolkit they belong to.

    This endpoint accepts requests with or without authentication (open passthrough).
    """
    if getattr(request.state, "is_human_session", False):
        username = getattr(request.state, "username", None)
        if username is None:
            async with get_db() as db:
                async with db.execute(
                    "SELECT username FROM users WHERE password_hash IS NOT NULL "
                    "ORDER BY created_at ASC LIMIT 1"
                ) as cur:
                    row = await cur.fetchone()
            username = row[0] if row else "unknown"
        return {"logged_in": True, "username": username}
    elif getattr(request.state, "is_admin", False):
        # Trusted-subnet passthrough — admin access without an explicit session
        return {
            "logged_in": False,
            "admin": True,
            "note": "Trusted-subnet access. Log in for a named session.",
        }
    elif getattr(request.state, "toolkit_id", None):
        return {"logged_in": False, "agent_key": True, "toolkit_id": request.state.toolkit_id}
    else:
        return {"logged_in": False, "agent_key": False}
