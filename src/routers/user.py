"""User account management — create, login, logout.

Single root account per instance. No multi-user, no roles.

Endpoints:
  POST /user/create  — create root account (one-time, 410 after first call)
  POST /user/login   — username + password → httpOnly JWT cookie
  POST /user/token   — OAuth2 password grant → Bearer JWT (for Swagger UI Authorize dialog)
  POST /user/logout  — clears session cookie (human session required)

Password reset is CLI-only:
  docker exec jentic-mini python3 -m jentic reset-password
"""
import time
import uuid

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from src.validators import NormModel

from src.auth import _make_jwt, JWT_TTL_SECONDS
from src.db import get_db, get_setting, set_setting, setup_state
from src.models import UserOut

import bcrypt as _bcrypt

router = APIRouter(prefix="/user", tags=["user"])


# ── Models ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str

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
)
async def create_user(body: UserCreate, response: Response):
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
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    pw_hash = _bcrypt.hashpw(body.password.encode(), _bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())

    async with get_db() as db:
        await db.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, body.username.strip(), pw_hash),
        )
        await db.commit()

    await set_setting("account_created", "1")

    # Auto-login — issue session cookie immediately
    jwt_secret = state["jwt_secret"]
    token = _make_jwt(jwt_secret)
    response.set_cookie(
        "jentic_session",
        token,
        httponly=True,
        samesite="strict",
        max_age=JWT_TTL_SECONDS,
    )

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
async def login(request: Request, response: Response, redirect_to: str | None = None):
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

    if not row or not _bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise HTTPException(
            401,
            detail={
                "error": "invalid_credentials",
                "message": "Username or password incorrect.",
            },
        )

    state = await setup_state()
    token = _make_jwt(state["jwt_secret"])

    if redirect_to:
        from fastapi.responses import RedirectResponse
        redir = RedirectResponse(url=redirect_to, status_code=303)
        redir.set_cookie("jentic_session", token, httponly=True, samesite="strict", max_age=JWT_TTL_SECONDS)
        return redir

    response.set_cookie(
        "jentic_session",
        token,
        httponly=True,
        samesite="strict",
        max_age=JWT_TTL_SECONDS,
    )

    return {"message": "Logged in.", "username": row["username"]}


@router.post(
    "/token",
    summary="OAuth2 password grant — returns Bearer JWT",
    response_description="Access token for use in Authorization: Bearer header",
)
async def token(
    grant_type: str = Form(default="password"),
    username: str = Form(...),
    password: str = Form(...),
    scope: str = Form(default=""),
):
    """OAuth2 password grant endpoint.

    Swagger UI's **Authorize** dialog uses this automatically when you fill in
    the *HumanLogin* username + password fields. Returns a Bearer JWT that
    Swagger UI injects as `Authorization: Bearer ...` on all subsequent calls.

    This is functionally equivalent to `POST /user/login` but returns the token
    in the response body rather than as a cookie — the standard OAuth2 pattern
    expected by Swagger UI.
    """
    if grant_type != "password":
        raise HTTPException(400, detail={"error": "unsupported_grant_type"})

    async with get_db() as db:
        db.row_factory = __import__("aiosqlite").Row
        async with db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ) as cur:
            row = await cur.fetchone()

    if not row or not _bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise HTTPException(
            401,
            detail={"error": "invalid_client", "error_description": "Username or password incorrect."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    state = await setup_state()
    access_token = _make_jwt(state["jwt_secret"])

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
    response.delete_cookie("jentic_session")
    return {"message": "Logged out."}


@router.get(
    "/me",
    summary="Check current session status",
    response_model=UserOut,
)
async def me(request: Request):
    """Returns current session info. Useful for UI to check if logged in."""
    if getattr(request.state, "is_human_session", False):
        async with get_db() as db:
            async with db.execute("SELECT username FROM users LIMIT 1") as cur:
                row = await cur.fetchone()
        return {"logged_in": True, "username": row[0] if row else "unknown"}
    elif getattr(request.state, "is_admin", False):
        # Trusted-subnet passthrough — admin access without an explicit session
        return {"logged_in": False, "admin": True, "note": "Trusted-subnet access. Log in for a named session."}
    elif getattr(request.state, "toolkit_id", None):
        return {"logged_in": False, "agent_key": True, "toolkit_id": request.state.toolkit_id}
    else:
        return {"logged_in": False, "agent_key": False}
