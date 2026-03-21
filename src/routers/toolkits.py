"""Toolkits router — scoped bundles of upstream API credentials with client API keys and access policies.

A toolkit is the central agent identity in Jentic:
- Has its own client API key(s) issued to the agent (scope: execute by default)
- Bundles upstream API credentials from the vault (injected by the broker on outbound calls)
- Has an access control policy (allow/deny rules by API/method/path)

This models the Jentic v2 design spec's toolkits concept exactly.
"""
import json
import re as _re
import secrets
import time
import uuid

import yaml

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from src.validators import NormModel
from typing import Any

from src.auth import default_allowed_ips
from src.db import get_db, DEFAULT_TOOLKIT_ID
import src.vault as vault
from src.models import (
    ToolkitOut, ToolkitKeyOut, ToolkitKeyCreated,
    CredentialBindingOut, PermissionRule, PermissionsPatch,
)

router = APIRouter(prefix="/toolkits")
policy_router = APIRouter()  # mounted separately with tags=["permissions"], prefix="/toolkits" added at include time


# ── Models ────────────────────────────────────────────────────────────────────

class ToolkitCreate(NormModel):
    name: str
    description: str | None = None
    simulate: bool = False
    initial_key_label: str | None = Field(None, description="Label for the first key created with this toolkit (e.g. 'Agent A')")
    initial_key_allowed_ips: list[str] | None = Field(None, description="IP allowlist for the first key. NULL = unrestricted.")


class ToolkitPatch(NormModel):
    name: str | None = None
    description: str | None = None
    simulate: bool | None = None


class KeyCreate(NormModel):
    label: str | None = Field(None, description="Human-readable label, e.g. 'Agent A', 'Staging bot'")
    allowed_ips: list[str] | None = Field(None, description="IP allowlist for this key only. NULL = unrestricted.")


class KeyOut(BaseModel):
    id: str
    label: str | None
    allowed_ips: list[str] | None
    created_at: float
    revoked_at: float | None = None
    # api_key only returned on create (shown once, never again)


class ToolkitCredentialAdd(NormModel):
    credential_id: str




# Keep PolicyRule as an alias for backward compat within this file
PolicyRule = PermissionRule




# System safety rules — always appended after agent rules.
# Visible to agents via GET /toolkits/{id}/credentials/{cred_id}/permissions.
SYSTEM_SAFETY_RULES: list[dict] = [
    {
        "effect": "deny",
        "path": r"admin|pay|billing|webhook|secret|token",
        "_system": True,
        "_comment": "Deny requests to sensitive path segments",
    },
    {
        "effect": "deny",
        "methods": ["POST", "PUT", "PATCH", "DELETE"],
        "_system": True,
        "_comment": "Deny write methods by default — add an explicit allow rule above to unlock specific writes",
    },
    {
        "effect": "allow",
        "_system": True,
        "_comment": "Allow everything else (reads pass through by default)",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a display name to a URL-safe hyphen slug.
    'My ElevenLabs Toolkit' → 'my-elevenlabs-toolkit'
    Lowercased, non-alphanumeric runs replaced with hyphens, leading/trailing stripped.
    """
    slug = name.lower()
    slug = _re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "toolkit"


def _gen_toolkit_key() -> str:
    """Generate a toolkit API key (col_ prefix)."""
    return "tk_" + secrets.token_urlsafe(24)


def _toolkit_links(toolkit_id: str) -> dict:
    return {
        "self": f"/toolkits/{toolkit_id}",
        "keys": f"/toolkits/{toolkit_id}/keys",
        "credentials": f"/toolkits/{toolkit_id}/credentials",
        "search": f"/search?toolkit_id={toolkit_id}",
    }


def _generate_policy_summary(rules: list[dict]) -> str:
    """Human-readable one-liner for a set of agent rules."""
    if not rules:
        return "Read-only (system safety rules apply; add allow rules to unlock writes)."
    allow_rules = [r for r in rules if r.get("effect") == "allow"]
    deny_rules = [r for r in rules if r.get("effect") == "deny"]
    parts = []
    if allow_rules:
        parts.append(f"{len(allow_rules)} allow rule(s)")
    if deny_rules:
        parts.append(f"{len(deny_rules)} deny rule(s)")
    return f"Agent rules: {', '.join(parts)}. System safety rules apply below."


def _check_policy(agent_rules: list[dict], operation_id: str | None,
                  method: str | None = None,
                  path: str | None = None) -> tuple[bool, str]:
    """
    Evaluate access for a request against a credential's rules.
    Order: agent rules → system safety rules → explicit allow-all.
    Returns (allowed: bool, reason: str).
    """
    import re

    all_rules = list(agent_rules) + SYSTEM_SAFETY_RULES

    for rule in all_rules:
        effect = rule.get("effect", "allow")
        methods = rule.get("methods")
        path_regex = rule.get("path")
        operation_regexes = rule.get("operations")

        matched = True

        # Method match
        if matched and methods:
            if method and method.upper() not in [m.upper() for m in methods]:
                matched = False

        # Path regex match (re.search — substring by default)
        if matched and path_regex:
            if path:
                try:
                    if not re.search(path_regex, path, re.IGNORECASE):
                        matched = False
                except re.error:
                    matched = False
            else:
                matched = False

        # Operations regex match — any regex in the list matches
        if matched and operation_regexes:
            if operation_id:
                try:
                    op_match = any(
                        re.search(pat, operation_id, re.IGNORECASE)
                        for pat in operation_regexes
                    )
                    if not op_match:
                        matched = False
                except re.error:
                    matched = False
            else:
                matched = False

        if matched:
            comment = rule.get("_comment", "")
            return (effect == "allow"), f"Matched rule ({effect}){': ' + comment if comment else ''}"

    return True, "Default action: allow"


# ── Routes ────────────────────────────────────────────────────────────────────

def _strip_key(d: dict) -> dict:
    """Remove api_key from a toolkit dict. Keys are write-once (shown only on creation)."""
    return {k: v for k, v in d.items() if k != "api_key"}


@router.post("", status_code=201, summary="Create a toolkit — scoped bundle of upstream API credentials with a client API key", response_model=ToolkitOut)
async def create_toolkit(body: ToolkitCreate):
    """Creates a toolkit: a named bundle of upstream API credentials with a scoped client API key for the agent.
    Returns a toolkit API key (col_xxx) — shown once, not recoverable.
    Bind credentials via POST /toolkits/{id}/credentials.
    Set access policy via PUT /toolkits/{id}/permissions.
    Agents use toolkit keys to call the broker; only bound credentials are injected.
    """
    coll_id = _slugify(body.name)
    api_key = _gen_toolkit_key()
    key_id = "ck_" + str(uuid.uuid4())[:8]
    key_label = body.initial_key_label or "Default key"
    allowed_ips_json = json.dumps(body.initial_key_allowed_ips) if body.initial_key_allowed_ips is not None else json.dumps(default_allowed_ips()) if default_allowed_ips() else None
    now = time.time()

    async with get_db() as db:
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (coll_id,)) as cur:
            if await cur.fetchone():
                raise HTTPException(409, f"A toolkit with slug '{coll_id}' already exists. Choose a different name.")
        await db.execute(
            """INSERT INTO toolkits (id, name, description, api_key, simulate, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (coll_id, body.name, body.description, api_key, int(body.simulate), now, now)
        )
        # Store the key in toolkit_keys (authoritative for auth)
        await db.execute(
            """INSERT INTO toolkit_keys (id, toolkit_id, api_key, label, allowed_ips, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, coll_id, api_key, key_label, allowed_ips_json, now)
        )
        # Create default read-only policy (no agent rules; system safety rules apply)
        policy_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO toolkit_policies (id, toolkit_id, default_action, rules, summary)
               VALUES (?, ?, 'allow', '[]', 'Read-only (system safety rules apply; add allow rules to unlock writes).')""",
            (policy_id, coll_id)
        )
        await db.commit()

    return {
        "id": coll_id,
        "name": body.name,
        "description": body.description,
        "simulate": body.simulate,
        "created_at": now,
        "keys": [
            {
                "id": key_id,
                "label": key_label,
                "api_key": api_key,  # shown ONLY here, never again
                "allowed_ips": body.initial_key_allowed_ips,
                "created_at": now,
            }
        ],
        "_notice": "Store api_key securely — it will not be shown again. Add more keys via POST /toolkits/{id}/keys.",
        "_links": {**_toolkit_links(coll_id), "keys": f"/toolkits/{coll_id}/keys"},
    }


@router.get("", summary="List toolkits", response_model=list[ToolkitOut])
async def list_toolkits(request: Request):
    """List all toolkits."""
    async with get_db() as db:
        async with db.execute("SELECT id, name, description, simulate, created_at FROM toolkits") as cur:
            rows = await cur.fetchall()
    return [
        {
            "id": r[0], "name": r[1], "description": r[2],
            "simulate": bool(r[3]),
            "created_at": r[4],
            "_links": {**_toolkit_links(r[0]), "keys": f"/toolkits/{r[0]}/keys"},
        }
        for r in rows
    ]


def _toolkit_to_markdown(data: dict) -> str:
    """Render toolkit detail as a human-readable Markdown document."""
    lines = [
        f"# Toolkit: {data.get('name') or data['id']}",
        "",
    ]
    if data.get("description"):
        lines += [data["description"], ""]
    lines += [
        f"**ID:** `{data['id']}`  ",
        f"**Simulate mode:** {'yes' if data.get('simulate') else 'no'}  ",
        "",
    ]

    credentials = data.get("credentials", [])
    if credentials:
        lines += ["## Bound Credentials", ""]
        for cred in credentials:
            lines.append(f"### `{cred['credential_id']}`")
            if cred.get("label"):
                lines.append(f"- **Label:** {cred['label']}")
            if cred.get("api_id"):
                lines.append(f"- **API:** `{cred['api_id']}`")
            user_rules = [r for r in cred.get("permissions", []) if not r.get("_system")]
            if user_rules:
                lines.append("- **Custom permissions:**")
                for rule in user_rules:
                    effect = rule.get("effect", "allow").upper()
                    methods = ", ".join(rule.get("methods", ["*"]))
                    path = rule.get("path", "*")
                    lines.append(f"  - `{effect}` `{methods}` `{path}`")
            lines.append("")
    else:
        lines += ["## Bound Credentials", "", "_No credentials bound._", ""]

    bound_apis = data.get("bound_apis", [])
    if bound_apis:
        lines += ["## Accessible APIs", ""]
        for api in bound_apis:
            lines.append(f"- `{api}`")
        lines.append("")

    return "\n".join(lines)


_TOOLKIT_CONTENT_TYPES = {
    "application/json": {"schema": {"type": "object"}},
    "application/yaml": {"schema": {"type": "string", "description": "Toolkit detail as YAML"}},
    "text/markdown":    {"schema": {"type": "string", "description": "LLM-friendly toolkit summary"}},
}


@router.get(
    "/{toolkit_id}",
    summary="Get toolkit — metadata, bound upstream API credentials, client API keys, and policy summary",
    responses={200: {"description": "Toolkit detail — format controlled by Accept header.", "content": _TOOLKIT_CONTENT_TYPES}},
)
async def get_toolkit(toolkit_id: str, request: Request):
    """Get toolkit with all inline context: metadata, bound upstream API credentials, client API key count, and policy summary.
    The default toolkit implicitly contains ALL upstream API credentials — no explicit binding needed.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, description, simulate, created_at FROM toolkits WHERE id=?",
            (toolkit_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, f"Toolkit '{toolkit_id}' not found")

    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            # Default toolkit sees all credentials implicitly
            async with db.execute(
                "SELECT id, id, label, api_id, created_at FROM credentials ORDER BY created_at DESC",
            ) as cur:
                cred_rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT cc.id, cc.credential_id, c.label, c.api_id, cc.created_at
                   FROM toolkit_credentials cc
                   JOIN credentials c ON cc.credential_id = c.id
                   WHERE cc.toolkit_id = ?""",
                (toolkit_id,)
            ) as cur:
                cred_rows = await cur.fetchall()

        # Load per-credential permissions
        cred_ids = [r[1] for r in cred_rows]
        cred_policies: dict[str, list] = {}
        if cred_ids:
            placeholders = ",".join("?" * len(cred_ids))
            async with db.execute(
                f"SELECT credential_id, rules FROM credential_policies WHERE credential_id IN ({placeholders})",
                cred_ids
            ) as cur:
                for pol_row in await cur.fetchall():
                    cred_policies[pol_row[0]] = json.loads(pol_row[1])

    bound_apis = sorted({r[3] for r in cred_rows if r[3]})
    credentials = [
        {
            "credential_id": r[1],
            "label": r[2],
            "api_id": r[3],
            "bound_at": r[4],
            "permissions": cred_policies.get(r[1], []) + SYSTEM_SAFETY_RULES,
            "_links": {
                "permissions": f"/toolkits/{toolkit_id}/credentials/{r[1]}/permissions",
            },
        }
        for r in cred_rows
    ]

    data = {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "simulate": bool(row[3]),
        "created_at": row[4],
        "bound_apis": bound_apis,
        "credentials": credentials,
        "_links": _toolkit_links(toolkit_id),
    }

    accept = request.headers.get("accept", "application/json")
    if "application/yaml" in accept:
        return Response(
            content=yaml.dump(data, allow_unicode=True, sort_keys=False),
            media_type="application/yaml",
        )
    if "text/markdown" in accept:
        return Response(
            content=_toolkit_to_markdown(data),
            media_type="text/markdown; charset=utf-8",
        )
    return data


@router.patch("/{toolkit_id}", summary="Update toolkit — rename or update description", response_model=ToolkitOut)
async def patch_toolkit(toolkit_id: str, body: ToolkitPatch):
    async with get_db() as db:
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (toolkit_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Toolkit '{toolkit_id}' not found")
        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.description is not None:
            updates["description"] = body.description
        if body.simulate is not None:
            updates["simulate"] = int(body.simulate)
        if updates:
            updates["updated_at"] = time.time()
            set_clause = ", ".join(f"{k}=?" for k in updates)
            await db.execute(
                f"UPDATE toolkits SET {set_clause} WHERE id=?",
                list(updates.values()) + [toolkit_id]
            )
            await db.commit()
    return await get_toolkit(toolkit_id)


@router.delete("/{toolkit_id}", status_code=204, summary="Delete toolkit and revoke all its client API keys")
async def delete_toolkit(toolkit_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM toolkits WHERE id=?", (toolkit_id,))
        await db.commit()


# ── Toolkit Keys ───────────────────────────────────────────────────────────
# One toolkit can have many access keys — one per agent/client.
# Each key can be individually revoked without affecting other agents.
# IP restrictions live at the key level, not the toolkit level.

@router.post("/{toolkit_id}/keys", status_code=201, summary="Issue a new client API key for this toolkit", response_model=ToolkitKeyCreated)
async def create_toolkit_key(toolkit_id: str, body: KeyCreate):
    """Issues an additional client API key (tk_xxx) for this toolkit. Hand this key to the agent. Optionally restrict by IP (CIDR list). Returned once — not recoverable."""
    async with get_db() as db:
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (toolkit_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Toolkit '{toolkit_id}' not found")

    api_key = _gen_toolkit_key()
    key_id = "ck_" + str(uuid.uuid4())[:8]
    allowed_ips_json = json.dumps(body.allowed_ips) if body.allowed_ips is not None else json.dumps(default_allowed_ips()) if default_allowed_ips() else None
    now = time.time()

    async with get_db() as db:
        await db.execute(
            """INSERT INTO toolkit_keys (id, toolkit_id, api_key, label, allowed_ips, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, toolkit_id, api_key, body.label, allowed_ips_json, now)
        )
        await db.commit()

    return {
        "id": key_id,
        "toolkit_id": toolkit_id,
        "label": body.label,
        "key": api_key,  # shown ONLY here, never again
        "allowed_ips": body.allowed_ips,
        "created_at": now,
        "_notice": "Store key securely — it will not be shown again.",
        "_links": {
            "toolkit": f"/toolkits/{toolkit_id}",
            "revoke": f"/toolkits/{toolkit_id}/keys/{key_id}",
        },
    }


@router.get("/{toolkit_id}/keys", summary="List client API keys for this toolkit — metadata only, no secret values")
async def list_toolkit_keys(toolkit_id: str):
    """
    List all access keys for this toolkit.

    Active and revoked keys are shown (revoked keys have `revoked_at` set).
    The `api_key` value is never returned — only the key ID and metadata.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (toolkit_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Toolkit '{toolkit_id}' not found")
        async with db.execute(
            """SELECT id, label, allowed_ips, created_at, revoked_at
               FROM toolkit_keys WHERE toolkit_id=?
               ORDER BY created_at ASC""",
            (toolkit_id,)
        ) as cur:
            rows = await cur.fetchall()

    return {
        "toolkit_id": toolkit_id,
        "keys": [
            {
                "id": r[0],
                "label": r[1],
                "allowed_ips": json.loads(r[2]) if r[2] else None,
                "created_at": r[3],
                "revoked_at": r[4],
                "status": "revoked" if r[4] else "active",
                "_links": {
                    "revoke": f"/toolkits/{toolkit_id}/keys/{r[0]}",
                },
            }
            for r in rows
        ],
        "_links": {"toolkit": f"/toolkits/{toolkit_id}"},
    }


@router.patch("/{toolkit_id}/keys/{key_id}", summary="Update a client API key — rename or change IP restrictions", response_model=ToolkitKeyOut)
async def patch_toolkit_key(toolkit_id: str, key_id: str, body: KeyCreate):
    """Update label or IP restrictions on a client API key. Cannot change the key value itself."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM toolkit_keys WHERE id=? AND toolkit_id=?",
            (key_id, toolkit_id)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Key '{key_id}' not found in toolkit '{toolkit_id}'")

        updates: dict = {}
        if body.label is not None:
            updates["label"] = body.label
        if body.allowed_ips is not None:
            updates["allowed_ips"] = json.dumps(body.allowed_ips) if body.allowed_ips else None

        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            await db.execute(
                f"UPDATE toolkit_keys SET {set_clause} WHERE id=?",
                list(updates.values()) + [key_id]
            )
            await db.commit()

    # Return updated key metadata (no api_key)
    async with get_db() as db:
        async with db.execute(
            "SELECT id, label, allowed_ips, created_at, revoked_at FROM toolkit_keys WHERE id=?",
            (key_id,)
        ) as cur:
            row = await cur.fetchone()
    return {
        "id": row[0], "toolkit_id": toolkit_id, "label": row[1],
        "allowed_ips": json.loads(row[2]) if row[2] else None,
        "created_at": row[3], "revoked_at": row[4],
        "status": "revoked" if row[4] else "active",
    }


@router.delete("/{toolkit_id}/keys/{key_id}", status_code=204, summary="Revoke a client API key")
async def revoke_toolkit_key(toolkit_id: str, key_id: str):
    """
    Revoke a single access key.

    Other keys for this toolkit remain active. The revoked key immediately
    stops working — any agent using it will receive 401 on their next request.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM toolkit_keys WHERE id=? AND toolkit_id=?",
            (key_id, toolkit_id)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Key '{key_id}' not found in toolkit '{toolkit_id}'")
        await db.execute(
            "UPDATE toolkit_keys SET revoked_at=? WHERE id=?",
            (time.time(), key_id)
        )
        await db.commit()


# ── Toolkit Credentials ────────────────────────────────────────────────────

@router.post("/{toolkit_id}/credentials", status_code=201, summary="Bind an upstream API credential to this toolkit — enable broker injection", response_model=CredentialBindingOut)
async def add_credential_to_toolkit(toolkit_id: str, body: ToolkitCredentialAdd, request: Request):
    """Enrolls an existing upstream API credential in this toolkit. The broker automatically injects it into outbound calls for the API it's bound to, when the agent calls using this toolkit's client API key."""
    if not getattr(request.state, "is_admin", False):
        raise HTTPException(403, "Only the admin key can modify toolkit credentials.")
    async with get_db() as db:
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (toolkit_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Toolkit '{toolkit_id}' not found")
        async with db.execute("SELECT id, label FROM credentials WHERE id=?",
                               (body.credential_id,)) as cur:
            cred = await cur.fetchone()
        if not cred:
            raise HTTPException(404, f"Credential '{body.credential_id}' not found")

        cc_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO toolkit_credentials (id, toolkit_id, credential_id, alias, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (cc_id, toolkit_id, body.credential_id, cred[1], time.time())
            )
            await db.commit()
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(409, "Credential already in toolkit")
            raise

    return {
        "id": cc_id,
        "toolkit_id": toolkit_id,
        "credential_id": body.credential_id,
        "credential_label": cred[1],
    }


@router.get("/{toolkit_id}/credentials", summary="List upstream API credentials bound to this toolkit", response_model=list[CredentialBindingOut])
async def list_toolkit_credentials(toolkit_id: str, request: Request):
    """List upstream API credentials bound to this toolkit.
    Admin (human session) may list any toolkit's credentials.
    Agents may list credentials for their own toolkit only.
    """
    is_admin = getattr(request.state, "is_admin", False)
    caller_toolkit = getattr(request.state, "toolkit_id", None)
    if not is_admin:
        if not caller_toolkit:
            raise HTTPException(403, "Authentication required to list toolkit credentials.")
        if caller_toolkit != toolkit_id:
            raise HTTPException(403, "Agents may only list credentials for their own toolkit.")
    async with get_db() as db:
        async with db.execute(
            """SELECT cc.id, cc.credential_id, c.label, c.api_id, cc.created_at
               FROM toolkit_credentials cc
               JOIN credentials c ON cc.credential_id = c.id
               WHERE cc.toolkit_id = ?""",
            (toolkit_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "credential_id": r[1],
            "credential_label": r[2],
            "api_id": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


@router.delete("/{toolkit_id}/credentials/{credential_id}", status_code=204, summary="Unbind an upstream API credential from this toolkit")
async def remove_credential_from_toolkit(toolkit_id: str, credential_id: str):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM toolkit_credentials WHERE toolkit_id=? AND credential_id=?",
            (toolkit_id, credential_id)
        )
        await db.commit()


# ── Credential-scoped Permissions ────────────────────────────────────────────

@policy_router.get(
    "/{toolkit_id}/credentials/{cred_id}/permissions",
    summary="Get the permission rules for a specific credential in this toolkit",
    tags=["toolkits"],
    response_model=list[PermissionRule],
)
async def get_credential_permissions(toolkit_id: str, cred_id: str):
    """Returns all rules in evaluation order for this credential: agent-defined rules first,
    then the immutable system safety rules appended by the server. First match wins.

    Since rules are scoped to a single credential (which is bound to a specific API),
    path and operation patterns apply only to calls made using this credential.
    System rules are tagged `_system: true` — they cannot be removed.
    """
    async with get_db() as db:
        # Verify credential belongs to this toolkit (or is accessible)
        async with db.execute(
            """SELECT c.id FROM credentials c
               LEFT JOIN toolkit_credentials tc ON c.id = tc.credential_id AND tc.toolkit_id = ?
               WHERE c.id = ?""",
            (toolkit_id, cred_id),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, f"Credential '{cred_id}' not found in toolkit '{toolkit_id}'")

        async with db.execute(
            "SELECT rules FROM credential_policies WHERE credential_id=?", (cred_id,)
        ) as cur:
            pol = await cur.fetchone()

    agent_rules = json.loads(pol[0]) if pol else []
    return agent_rules + SYSTEM_SAFETY_RULES


@policy_router.put(
    "/{toolkit_id}/credentials/{cred_id}/permissions",
    summary="Replace permission rules for a specific credential",
    tags=["toolkits"],
    response_model=list[PermissionRule],
)
async def set_credential_permissions(toolkit_id: str, cred_id: str, body: list[PolicyRule]):
    """Replaces the entire agent rule list for this credential.
    System safety rules are always appended server-side and cannot be removed.
    Use `PATCH` to add or remove individual rules without replacing the full list.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM credentials WHERE id=?", (cred_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"Credential '{cred_id}' not found")

    rules_list = [r.model_dump(exclude_none=True) for r in body]
    return await _write_credential_permissions(cred_id, rules_list)


@policy_router.patch(
    "/{toolkit_id}/credentials/{cred_id}/permissions",
    summary="Add or remove individual permission rules for a specific credential",
    tags=["toolkits"],
    response_model=list[PermissionRule],
)
async def patch_credential_permissions(toolkit_id: str, cred_id: str, body: PermissionsPatch):
    """Incrementally update rules for this credential without replacing the full list.

    - `add`: rules appended (deduplicated)
    - `remove`: rules removed by exact match

    Example — unlock TTS writes for this credential:
    ```json
    {"add": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}]}
    ```
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT rules FROM credential_policies WHERE credential_id=?", (cred_id,)
        ) as cur:
            row = await cur.fetchone()

    current_rules: list[dict] = json.loads(row[0]) if row else []

    if body.remove:
        remove_set = [r.model_dump(exclude_none=True) for r in body.remove]
        current_rules = [r for r in current_rules if r not in remove_set]

    if body.add:
        existing = set(json.dumps(r, sort_keys=True) for r in current_rules)
        for rule in body.add:
            rule_dict = rule.model_dump(exclude_none=True)
            if json.dumps(rule_dict, sort_keys=True) not in existing:
                current_rules.append(rule_dict)
                existing.add(json.dumps(rule_dict, sort_keys=True))

    return await _write_credential_permissions(cred_id, current_rules)


async def _write_credential_permissions(credential_id: str, rules_list: list[dict]) -> list:
    """Persist agent rules for a credential and return the flat effective rule list."""
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rules_list]
    summary = _generate_policy_summary(clean)
    rules_json = json.dumps(clean)
    now = time.time()
    policy_id = str(uuid.uuid4())

    async with get_db() as db:
        await db.execute(
            """INSERT INTO credential_policies (id, credential_id, rules, summary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(credential_id) DO UPDATE SET
                 rules=excluded.rules,
                 summary=excluded.summary,
                 updated_at=excluded.updated_at""",
            (policy_id, credential_id, rules_json, summary, now, now)
        )
        await db.commit()

    return clean + SYSTEM_SAFETY_RULES


# ── Policy Enforcement (called by broker) ─────────────────────────────────────

async def check_credential_policy(
    credential_id: str,
    operation_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> tuple[bool, str]:
    """Check if an operation is permitted by the credential's policy rules.
    Returns (allowed: bool, reason: str).
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT rules FROM credential_policies WHERE credential_id=?",
            (credential_id,)
        ) as cur:
            row = await cur.fetchone()

    agent_rules = json.loads(row[0]) if row else []
    return _check_policy(agent_rules, operation_id, method, path)


# keep old name as alias so access_requests.py imports don't break during transition
async def check_toolkit_policy(
    toolkit_id: str,
    operation_id: str | None = None,
    method: str | None = None,
    api_host: str | None = None,
    path: str | None = None,
) -> tuple[bool, str]:
    """Deprecated alias — use check_credential_policy. Falls back to empty rules."""
    return _check_policy([], operation_id, method, path)

