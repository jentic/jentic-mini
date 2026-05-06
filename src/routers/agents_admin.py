"""Human-administered agent identities and toolkit grants."""

from __future__ import annotations

import json
import time
from typing import Annotated, Literal

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from src.agent_identity_util import extract_jwks_public_key_x, wiped_agent_jwks_json
from src.auth import require_human_session
from src.db import DB_PATH, get_db


router = APIRouter(prefix="/agents", tags=["agents"])


async def _admin_username(request: Request) -> str:
    async with get_db() as db:
        async with db.execute("SELECT username FROM users LIMIT 1") as cur:
            row = await cur.fetchone()
    return row[0] if row else "admin"


class GrantBody(BaseModel):
    toolkit_id: str = Field(description="Toolkit to grant this agent")


@router.get("", dependencies=[Depends(require_human_session)])
async def list_agents(
    view: Annotated[
        Literal["active", "declined", "removed"],
        Query(
            description="active: not denied and not deregistered; declined: denied only; "
            "removed: soft-deleted (deregistered)"
        ),
    ] = "active",
    status: Annotated[
        str | None,
        Query(description="When view=active only: pending, approved, disabled"),
    ] = None,
):
    q = (
        "SELECT client_id, client_name, status, created_at, approved_at, "
        "disabled_at, denied_at, deleted_at FROM agents"
    )
    args: list = []
    if view == "active":
        q += " WHERE deleted_at IS NULL AND status != 'denied'"
        if status:
            q += " AND status=?"
            args.append(status)
    elif view == "declined":
        q += " WHERE deleted_at IS NULL AND status = 'denied'"
    else:
        q += " WHERE deleted_at IS NOT NULL"
    q += " ORDER BY created_at DESC"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(q, args) as cur:
            rows = await cur.fetchall()
    return {
        "agents": [
            {
                "client_id": r["client_id"],
                "client_name": r["client_name"],
                "status": r["status"],
                "created_at": r["created_at"],
                "approved_at": r["approved_at"],
                "disabled_at": r["disabled_at"],
                "denied_at": r["denied_at"],
                "deleted_at": r["deleted_at"],
            }
            for r in rows
        ]
    }


@router.get("/{agent_id}", dependencies=[Depends(require_human_session)])
async def get_agent(agent_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT client_id, client_name, status, jwks_json, created_at,
                      approved_at, approved_by, denied_at, disabled_at, deleted_at
               FROM agents WHERE client_id=?""",
            (agent_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Agent not found")
    try:
        jwks = json.loads(row["jwks_json"])
    except Exception:
        jwks = {}
    return {
        "client_id": row["client_id"],
        "client_name": row["client_name"],
        "status": row["status"],
        "jwks": jwks,
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
        "approved_by": row["approved_by"],
        "denied_at": row["denied_at"],
        "disabled_at": row["disabled_at"],
        "deleted_at": row["deleted_at"],
    }


@router.post("/{agent_id}/approve", dependencies=[Depends(require_human_session)])
async def approve_agent(agent_id: str, request: Request):
    who = await _admin_username(request)
    now = time.time()
    async with get_db() as db:
        async with db.execute(
            "SELECT status FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        if row[0] != "pending":
            raise HTTPException(400, f"Cannot approve agent in status {row[0]!r}")
        await db.execute(
            """UPDATE agents SET status='approved', approved_at=?, approved_by=?
               WHERE client_id=? AND deleted_at IS NULL""",
            (now, who, agent_id),
        )
        await db.commit()
    return {"client_id": agent_id, "status": "approved"}


@router.post(
    "/{agent_id}/deny",
    dependencies=[Depends(require_human_session)],
    summary="Decline registration",
)
async def deny_agent(agent_id: str):
    now = time.time()
    async with get_db() as db:
        async with db.execute(
            "SELECT status FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        if row[0] != "pending":
            raise HTTPException(400, f"Cannot deny agent in status {row[0]!r}")
        wiped = wiped_agent_jwks_json()
        await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_toolkit_grants WHERE client_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_nonces WHERE client_id=?", (agent_id,))
        await db.execute(
            """UPDATE agents SET status='denied', denied_at=?, jwks_json=?,
                   registration_token_hash=NULL, registration_token_expires_at=NULL
               WHERE client_id=? AND deleted_at IS NULL""",
            (now, wiped, agent_id),
        )
        await db.commit()
    return {"client_id": agent_id, "status": "denied"}


@router.post("/{agent_id}/disable", dependencies=[Depends(require_human_session)])
async def disable_agent(agent_id: str):
    now = time.time()
    async with get_db() as db:
        async with db.execute(
            "SELECT client_id FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Agent not found")
        await db.execute(
            "UPDATE agents SET status='disabled', disabled_at=? WHERE client_id=? AND deleted_at IS NULL",
            (now, agent_id),
        )
        await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (agent_id,))
        await db.commit()
    return {"client_id": agent_id, "status": "disabled"}


@router.post("/{agent_id}/enable", dependencies=[Depends(require_human_session)])
async def enable_agent(agent_id: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT status FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        if row[0] != "disabled":
            raise HTTPException(400, "Agent is not disabled")
        await db.execute(
            "UPDATE agents SET status='approved', disabled_at=NULL WHERE client_id=? AND deleted_at IS NULL",
            (agent_id,),
        )
        await db.commit()
    return {"client_id": agent_id, "status": "approved"}


@router.put("/{agent_id}/jwks", dependencies=[Depends(require_human_session)])
async def rotate_agent_jwks(agent_id: str, body: dict):
    jwks = body.get("jwks")
    if not isinstance(jwks, dict):
        raise HTTPException(400, "jwks object is required")
    try:
        extract_jwks_public_key_x(jwks)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    async with get_db() as db:
        async with db.execute(
            "SELECT client_id FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Agent not found")
        await db.execute(
            "UPDATE agents SET jwks_json=? WHERE client_id=? AND deleted_at IS NULL",
            (json.dumps(jwks), agent_id),
        )
        await db.commit()
    return {"client_id": agent_id, "jwks": jwks}


@router.delete(
    "/{agent_id}",
    status_code=204,
    dependencies=[Depends(require_human_session)],
    summary="Deregister agent (soft delete)",
)
async def delete_agent(agent_id: str):
    """Soft-delete for audit: revoke tokens, strip JWKS and registration secrets, drop grants."""
    now = time.time()
    wiped = wiped_agent_jwks_json()
    async with get_db() as db:
        async with db.execute(
            "SELECT deleted_at FROM agents WHERE client_id=?", (agent_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        if row[0] is not None:
            await db.commit()
            return
        await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_toolkit_grants WHERE client_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_nonces WHERE client_id=?", (agent_id,))
        await db.execute(
            """UPDATE agents SET deleted_at=?, jwks_json=?,
                   registration_token_hash=NULL, registration_token_expires_at=NULL
               WHERE client_id=?""",
            (now, wiped, agent_id),
        )
        await db.commit()


@router.post("/{agent_id}/grants", dependencies=[Depends(require_human_session)])
async def add_grant(agent_id: str, body: GrantBody, request: Request):
    who = await _admin_username(request)
    now = time.time()
    async with get_db() as db:
        async with db.execute(
            "SELECT client_id FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Agent not found")
        async with db.execute(
            "SELECT disabled FROM toolkits WHERE id=?", (body.toolkit_id,)
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                raise HTTPException(404, f"Toolkit '{body.toolkit_id}' not found")
            if row[0]:
                raise HTTPException(
                    409, f"Toolkit '{body.toolkit_id}' is disabled and cannot be granted"
                )
        await db.execute(
            """INSERT OR REPLACE INTO agent_toolkit_grants (client_id, toolkit_id, granted_at, granted_by)
               VALUES (?,?,?,?)""",
            (agent_id, body.toolkit_id, now, who),
        )
        await db.commit()
    return {"client_id": agent_id, "toolkit_id": body.toolkit_id, "granted_at": now}


@router.get("/{agent_id}/grants", dependencies=[Depends(require_human_session)])
async def list_grants(agent_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT toolkit_id, granted_at, granted_by FROM agent_toolkit_grants
               WHERE client_id=? ORDER BY granted_at ASC""",
            (agent_id,),
        ) as cur:
            rows = await cur.fetchall()
    return {
        "client_id": agent_id,
        "grants": [
            {
                "toolkit_id": r["toolkit_id"],
                "granted_at": r["granted_at"],
                "granted_by": r["granted_by"],
            }
            for r in rows
        ],
    }


@router.delete(
    "/{agent_id}/grants/{toolkit_id}",
    status_code=204,
    dependencies=[Depends(require_human_session)],
)
async def delete_grant(
    agent_id: str,
    toolkit_id: str = Path(..., description="Toolkit id to revoke"),
):
    async with get_db() as db:
        async with db.execute(
            "SELECT client_id FROM agents WHERE client_id=? AND deleted_at IS NULL", (agent_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Agent not found")
        await db.execute(
            "DELETE FROM agent_toolkit_grants WHERE client_id=? AND toolkit_id=?",
            (agent_id, toolkit_id),
        )
        await db.commit()
