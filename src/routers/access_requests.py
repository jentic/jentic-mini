"""Access Requests router — agent-initiated requests for credential access and permission changes.

Agents can request:
- grant: bind a specific upstream API credential to their toolkit, enabling calls to that API
  (use GET /credentials to discover credential IDs and labels first, then reference credential_id)
- modify_permissions: change the toolkit's fine-grained allow/deny rules for operations
  it already has credential access to

All requests require human approval. Toolkit ID is taken from the URL path — agents use their
own toolkit ID, admins can view and act on any toolkit's requests.

URL structure (nested under /toolkits):
  POST   /toolkits/{toolkit_id}/access-requests
  GET    /toolkits/{toolkit_id}/access-requests
  GET    /toolkits/{toolkit_id}/access-requests/{req_id}
  POST   /toolkits/{toolkit_id}/access-requests/{req_id}/approve
  POST   /toolkits/{toolkit_id}/access-requests/{req_id}/deny
  GET    /toolkits/{toolkit_id}/access-requests/approve/{req_id}  (HTML UI)
"""

import html
import json
import logging
import time
import uuid
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import Field

from src.auth import require_human_session
from src.db import get_db
from src.models import AccessRequestOut, PermissionRule
from src.routers.toolkits import write_credential_permissions
from src.utils import build_absolute_url
from src.validators import NormModel


log = logging.getLogger("jentic")

router = APIRouter()


# ── Request body ──────────────────────────────────────────────────────────────


class AccessRequestBody(NormModel):
    """Body for POST /toolkits/{id}/access-requests.

    **`type=grant`** — bind an upstream API credential to this toolkit:
    ```json
    {
      "type": "grant",
      "credential_id": "api.elevenlabs.io",
      "rules": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}],
      "reason": "I need to generate audio"
    }
    ```

    **`type=modify_permissions`** — update rules on a credential already bound to this toolkit:
    ```json
    {
      "type": "modify_permissions",
      "credential_id": "api.elevenlabs.io",
      "rules": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}],
      "reason": "I need write access to TTS only"
    }
    ```
    """

    type: Literal["grant", "modify_permissions"] = Field(
        description=(
            "`grant` — bind an upstream API credential to this toolkit. "
            "Requires `credential_id`; `rules` is optional (defaults to system safety rules only). "
            "`modify_permissions` — update permission rules on a credential already bound to this toolkit. "
            "Requires both `credential_id` and `rules`."
        )
    )
    credential_id: str = Field(
        description=(
            "The upstream API credential to act on. "
            "Discover available IDs and labels via `GET /credentials` or `GET /credentials?api_id=<host>`."
        )
    )
    rules: list[PermissionRule] = Field(
        default=[],
        description=(
            "Ordered list of permission rules. For `grant`, applied atomically when approved. "
            "For `modify_permissions`, replaces the current agent rules entirely. "
            "System safety rules (deny writes, deny sensitive paths) are always appended after these and cannot be removed.\n\n"
            "Each `PermissionRule` object — all fields except `effect` are optional and AND-combined:\n"
            '- `effect` *(required)*: `"allow"` or `"deny"`\n'
            '- `methods`: list of HTTP verbs to match, e.g. `["GET", "POST"]` — omit to match all\n'
            "- `path`: Python regex matched against the **path component only** of the upstream URL "
            "(host and query string are excluded). Uses `re.search()` — **substring match by default**, "
            "case-insensitive. Use `^`/`$` to anchor. `|` is regex OR.\n"
            '  - Unanchored: `"issues"` matches any path *containing* the word — often too broad\n'
            '  - Prefix: `"^/repos/myorg/myrepo/"` — everything under that path\n'
            '  - Exact: `"^/v1/voices$"` — only that specific endpoint\n'
            "  - **Tip:** always anchor with `^` when generating allow rules to avoid unintended matches\n"
            "- `operations`: list of regexes matched against the operation ID\n\n"
            "**Examples:**\n"
            "```json\n"
            '[{"effect": "allow", "methods": ["POST"], "path": "^/v1/text-to-speech$"}]\n'
            '[{"effect": "deny",  "path": "admin|billing|pay"}]\n'
            '[{"effect": "allow", "operations": ["^get_voices$", "^tts"]}]\n'
            "```"
        ),
    )
    api_id: str | None = Field(
        default=None,
        description="Optional. Shown in the human approval UI. Usually inferred automatically from the credential.",
    )
    reason: str | None = Field(
        default=None,
        description="Explain to the human why access is needed. Shown in the approval UI.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "grant",
                    "credential_id": "api.elevenlabs.io",
                    "rules": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}],
                    "reason": "I need to generate audio narration",
                },
                {
                    "type": "modify_permissions",
                    "credential_id": "api.elevenlabs.io",
                    "rules": [
                        {"effect": "allow", "methods": ["GET"]},
                        {"effect": "allow", "methods": ["POST"], "path": "text-to-speech"},
                    ],
                    "reason": "Requesting read access plus TTS writes",
                },
            ]
        }
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/{toolkit_id}/access-requests",
    status_code=202,
    summary="Request access — ask a human to grant a credential or adjust permissions",
    tags=["toolkits"],
    response_model=AccessRequestOut,
    openapi_extra={
        "requestBody": {
            "description": "Access request: type (grant/modify_permissions), credential_id, optional permission rules, and optional reason explaining why access is needed"
        }
    },
)
async def create_access_request(
    toolkit_id: Annotated[str, Path(description="Toolkit ID")],
    request: Request,
    body: AccessRequestBody,
):
    """Agent submits an access request. A human approves or denies it at the `approve_url`.

    **Workflow:**
    1. `GET /credentials?api_id=<host>` — find the `credential_id` you need
    2. `POST` this endpoint with `type`, `credential_id`, `rules`, and optional `reason`
    3. Return the `approve_url` to your user and poll `status` until `approved` or `denied`

    The toolkit ID in the URL must match the caller's own toolkit.
    Admin/human sessions may file requests on behalf of any toolkit.
    """
    caller_toolkit = getattr(request.state, "toolkit_id", None)
    is_admin = getattr(request.state, "is_admin", False)

    if caller_toolkit and not is_admin and caller_toolkit != toolkit_id:
        raise HTTPException(403, "You can only file access requests for your own toolkit.")

    req_id = "areq_" + str(uuid.uuid4())[:8]

    approve_url = build_absolute_url(request, f"/approve/{toolkit_id}/{req_id}")

    # Store payload as the flat fields relevant to this request type
    payload_dict = {
        "credential_id": body.credential_id,
        "rules": [r.model_dump(exclude_none=True) for r in body.rules],
    }
    if body.api_id:
        payload_dict["api_id"] = body.api_id

    async with get_db() as db:
        await db.execute(
            """INSERT INTO permission_requests
               (id, toolkit_id, type, payload, reason, status, user_url, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (
                req_id,
                toolkit_id,
                body.type,
                json.dumps(payload_dict),
                body.reason,
                approve_url,
                time.time(),
            ),
        )
        await db.commit()

    description = await _describe_request(body.type, payload_dict)

    return {
        "id": req_id,
        "status": "pending",
        "type": body.type,
        "toolkit_id": toolkit_id,
        "payload": payload_dict,
        "description": description,
        "reason": body.reason,
        "approve_url": approve_url,
        "message": "Access request created. Direct your user to approve_url to review and approve.",
        "_links": {
            "self": f"/toolkits/{toolkit_id}/access-requests/{req_id}",
            "approve_ui": approve_url,
            "poll": f"/toolkits/{toolkit_id}/access-requests/{req_id}",
        },
    }


@router.get("/{toolkit_id}/access-requests/approve/{req_id}", include_in_schema=False)
async def approval_ui(toolkit_id: str, req_id: str):
    """Redirect to the React SPA approval page. Kept for backward compat with old approve_urls."""
    return RedirectResponse(
        url=f"/approve/{quote(toolkit_id, safe='')}/{quote(req_id, safe='')}", status_code=302
    )


@router.get("/{toolkit_id}/access-requests/approve/{req_id}/legacy", include_in_schema=False)
async def approval_ui_legacy(toolkit_id: str, req_id: str):
    """Legacy server-rendered approval page (kept for reference)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, type, toolkit_id, reason, payload, status FROM permission_requests WHERE id=? AND toolkit_id=?",
            (req_id, toolkit_id),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)

    row_id, req_type, row_toolkit_id, reason, payload_json, status = row
    payload = json.loads(payload_json)
    description = await _describe_request(req_type, payload)

    resolved_html = ""
    if status == "pending":
        resolved_html = f"""
        <div id="actions">
          <button class="approve" onclick="resolve('approve')">✅ Approve</button>
          <button class="deny" onclick="resolve('deny')">❌ Deny</button>
        </div>
        <p id="result" style="display:none"></p>
        <script>
        async function resolve(action) {{
          document.getElementById('actions').style.display = 'none';
          const r = await fetch('/toolkits/{quote(toolkit_id, safe="")}/access-requests/{quote(req_id, safe="")}/' + action, {{
            method: 'POST',
            credentials: 'include',
          }});
          const data = await r.json();
          const el = document.getElementById('result');
          el.style.display = '';
          if (r.ok) {{
            el.textContent = action === 'approve' ? '✅ Approved.' : '❌ Denied.';
            el.style.color = action === 'approve' ? '#10b981' : '#ef4444';
          }} else {{
            el.textContent = 'Error: ' + (data.detail || JSON.stringify(data));
            el.style.color = '#ef4444';
            document.getElementById('actions').style.display = '';
          }}
        }}
        </script>"""
    else:
        resolved_html = f"<p><em>This request has already been resolved: <strong>{html.escape(status)}</strong></em></p>"

    body = f"""<!DOCTYPE html>
<html>
<head><title>Access Request — Jentic Mini</title>
<style>
  body {{ font-family: system-ui; max-width: 600px; margin: 40px auto; padding: 0 20px; background:#0f172a; color:#e2e8f0; }}
  h1 {{ color: #f8fafc; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; margin: 20px 0; }}
  .card p {{ margin: 6px 0; }}
  .label {{ color: #94a3b8; font-size: 0.85em; }}
  .status-pending {{ color: #f59e0b; }}
  .status-approved {{ color: #10b981; }}
  .status-denied {{ color: #ef4444; }}
  button {{ padding: 10px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; margin: 5px 5px 5px 0; font-weight: 600; }}
  .approve {{ background: #10b981; color: white; }}
  .deny {{ background: #ef4444; color: white; }}
  pre {{ background: #0f172a; color: #94a3b8; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; border: 1px solid #334155; }}
</style>
</head>
<body>
  <h1>🔐 Access Request</h1>
  <div class="card">
    <p><span class="label">Request ID</span><br>{html.escape(row_id)}</p>
    <p><span class="label">Type</span><br>{html.escape(req_type)}</p>
    <p><span class="label">Toolkit</span><br>{html.escape(row_toolkit_id or "N/A")}</p>
    <p><span class="label">Status</span><br><span class="status-{html.escape(status)}">{html.escape(status)}</span></p>
    <p><span class="label">What the agent is requesting</span><br>{html.escape(description)}</p>
    <p><span class="label">Reason from agent</span><br>{html.escape(reason) if reason else "<em>No reason provided</em>"}</p>
    <p><span class="label">Payload</span></p>
    <pre>{html.escape(json.dumps(payload, indent=2))}</pre>
  </div>
  {resolved_html}
</body>
</html>"""
    return HTMLResponse(body)


@router.get(
    "/{toolkit_id}/access-requests/{req_id}",
    summary="Poll an access request — check approval status",
    tags=["toolkits"],
    response_model=AccessRequestOut,
)
async def get_access_request(
    toolkit_id: Annotated[str, Path(description="Toolkit ID")],
    req_id: Annotated[str, Path(description="Access request ID (format: areq_xxxxxxxx)")],
    request: Request,
):
    """
    Poll the status of a specific access request.

    Poll this endpoint after directing the user to `approve_url`. Status transitions:
    `pending` → `approved` | `denied`

    On approval, the `payload` contains the exact data that was applied (credential bound,
    rules set, etc.). For programmatic polling, check `status` field only — `approved`
    means the side effects have already been applied and the toolkit is ready to use.
    """
    caller_toolkit = getattr(request.state, "toolkit_id", None)
    is_admin = getattr(request.state, "is_admin", False)

    if caller_toolkit and not is_admin and caller_toolkit != toolkit_id:
        raise HTTPException(403, "You can only view access requests for your own toolkit.")

    async with get_db() as db:
        async with db.execute(
            """SELECT id, toolkit_id, type, payload, reason, status, user_url, created_at, resolved_at
               FROM permission_requests WHERE id=? AND toolkit_id=?""",
            (req_id, toolkit_id),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, f"Access request '{req_id}' not found in toolkit '{toolkit_id}'")

    return {
        "id": row[0],
        "toolkit_id": row[1],
        "type": row[2],
        "payload": json.loads(row[3]),
        "reason": row[4],
        "status": row[5],
        "approve_url": row[6],
        "created_at": row[7],
        "resolved_at": row[8],
    }


@router.get(
    "/{toolkit_id}/access-requests",
    summary="List access requests for this toolkit",
    tags=["toolkits"],
    response_model=list[AccessRequestOut],
)
async def list_access_requests(
    toolkit_id: Annotated[str, Path(description="Toolkit ID")],
    request: Request,
    status: Annotated[
        str | None, Query(description="Filter by status (pending, approved, denied)")
    ] = None,
):
    """
    List access requests for a toolkit, newest first.

    Each item includes the full `payload` (credential ID, rules, etc.) and current `status`.
    Filter by `status=pending` to find outstanding requests awaiting approval.

    **`type` values:**
    - `grant` — agent is requesting a new credential be bound; `payload` contains `credential_id` and optional `rules`
    - `modify_permissions` — agent is requesting a rule change on an existing credential; `payload` contains `credential_id` and `rules`

    Agent keys see only their own toolkit's requests. Admin/human sessions may view any toolkit.
    """
    caller_toolkit = getattr(request.state, "toolkit_id", None)
    is_admin = getattr(request.state, "is_admin", False)

    if caller_toolkit and not is_admin and caller_toolkit != toolkit_id:
        raise HTTPException(403, "You can only list access requests for your own toolkit.")

    conditions = ["toolkit_id=?"]
    params: list = [toolkit_id]
    if status:
        conditions.append("status=?")
        params.append(status)

    where = "WHERE " + " AND ".join(conditions)

    async with get_db() as db:
        async with db.execute(
            f"""SELECT id, toolkit_id, type, payload, reason, status, user_url, created_at, resolved_at
               FROM permission_requests {where} ORDER BY created_at DESC LIMIT 100""",
            params,
        ) as cur:
            rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "toolkit_id": r[1],
            "type": r[2],
            "payload": json.loads(r[3] or "{}"),
            "reason": r[4],
            "status": r[5],
            "approve_url": r[6],
            "created_at": r[7],
            "resolved_at": r[8],
        }
        for r in rows
    ]


@router.post(
    "/{toolkit_id}/access-requests/{req_id}/approve",
    summary="Approve an access request (human session only)",
    tags=["toolkits"],
    response_model=AccessRequestOut,
)
async def approve_access_request(
    toolkit_id: Annotated[str, Path(description="Toolkit ID")],
    req_id: Annotated[str, Path(description="Access request ID to approve")],
    _: None = Depends(require_human_session),
):
    """
    Approve a pending access request (human or admin action — agent keys cannot do this).

    For `grant` requests: the upstream API credential is automatically bound to the toolkit.
    For `modify_permissions` requests: the new permission rules are applied immediately.
    """
    try:
        return await _resolve(toolkit_id, req_id, "approved")
    except HTTPException:
        raise
    except Exception:
        log.exception("Failed to approve access request %s", req_id)
        raise HTTPException(500, "Failed to process approval. Check server logs.")


@router.post(
    "/{toolkit_id}/access-requests/{req_id}/deny",
    summary="Deny an access request (human session only)",
    tags=["toolkits"],
    response_model=AccessRequestOut,
)
async def deny_access_request(
    toolkit_id: Annotated[str, Path(description="Toolkit ID")],
    req_id: Annotated[str, Path(description="Access request ID to deny")],
    _: None = Depends(require_human_session),
):
    """Deny a pending access request.

    Permanently rejects the request. The agent will receive a 403 error if it continues
    to attempt the operation that required the permission. To grant access later, the
    agent must file a new request.

    Parameters:
        toolkit_id: Toolkit ID containing the access request
        req_id: Access request ID (format: areq_xxxxxxxx)

    Returns:
        Updated access request with status='denied' and resolved_at timestamp.

    Auth: Requires human session (admin).
    """
    try:
        return await _resolve(toolkit_id, req_id, "denied")
    except HTTPException:
        raise
    except Exception:
        log.exception("Failed to deny access request %s", req_id)
        raise HTTPException(500, "Failed to process denial. Check server logs.")


# ── Internals ─────────────────────────────────────────────────────────────────


async def _resolve(toolkit_id: str, req_id: str, status: str) -> dict:
    async with get_db() as db:
        async with db.execute(
            "SELECT type, toolkit_id, payload, status FROM permission_requests WHERE id=? AND toolkit_id=?",
            (req_id, toolkit_id),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, f"Access request '{req_id}' not found in toolkit '{toolkit_id}'")

    if row[3] != "pending":
        raise HTTPException(409, f"Request already resolved (status: {row[3]})")

    req_type, row_toolkit_id, payload_json, _ = row
    payload = json.loads(payload_json)

    applied_effects = []
    if status == "approved":
        effect = await _apply_approved_request(req_type, row_toolkit_id, payload)
        if effect:
            applied_effects.append(effect)

    async with get_db() as db:
        await db.execute(
            "UPDATE permission_requests SET status=?, resolved_at=? WHERE id=?",
            (status, time.time(), req_id),
        )
        await db.commit()

    return {
        "id": req_id,
        "toolkit_id": toolkit_id,
        "type": req_type,
        "payload": payload,
        "status": status,
        "applied_effects": applied_effects,
    }


async def _describe_request(req_type: str, payload: dict) -> str:
    """Human-readable description of what the agent is requesting."""
    if req_type == "grant":
        cred_id = payload.get("credential_id")
        rules = payload.get("rules", [])
        if cred_id:
            async with get_db() as db:
                async with db.execute(
                    "SELECT label, api_id FROM credentials WHERE id=?", (cred_id,)
                ) as cur:
                    row = await cur.fetchone()
            base = (
                f"Grant access to credential '{row[0]}' (for {row[1] or 'unknown API'})"
                if row
                else f"Grant access to credential '{cred_id}'"
            )
        else:
            base = f"Grant access to a credential for {payload.get('api_id', 'unknown API')}"
        if rules:
            base += f" with {len(rules)} permission rule(s)"
        return base
    elif req_type == "modify_permissions":
        rules_count = len(payload.get("rules", []))
        return f"Modify permissions: {rules_count} rule(s)"
    return f"Request type: {req_type}"


async def _apply_approved_request(
    req_type: str, toolkit_id: str | None, payload: dict
) -> str | None:
    """Apply side effects when an access request is approved."""
    if req_type == "grant" and toolkit_id:
        cred_id = payload.get("credential_id")
        rules = payload.get("rules", [])
        effects = []
        if cred_id:
            try:
                async with get_db() as db:
                    async with db.execute(
                        "SELECT label FROM credentials WHERE id=?", (cred_id,)
                    ) as cur:
                        cred = await cur.fetchone()
                    if cred:
                        cc_id = str(uuid.uuid4())
                        await db.execute(
                            """INSERT OR IGNORE INTO toolkit_credentials
                               (id, toolkit_id, credential_id, alias, created_at)
                               VALUES (?, ?, ?, ?, ?)""",
                            (cc_id, toolkit_id, cred_id, cred[0], time.time()),
                        )
                        await db.commit()
                        effects.append(f"Credential '{cred[0]}' bound to toolkit {toolkit_id}")
                    else:
                        effects.append(f"Credential {cred_id} not found")
            except Exception as e:
                effects.append(f"Failed to bind credential: {e}")

        if rules and cred_id:
            try:
                clean_rules = [
                    r if isinstance(r, dict) else PermissionRule(**r).model_dump(exclude_none=True)
                    for r in rules
                ]
                await write_credential_permissions(cred_id, clean_rules)
                effects.append(f"{len(rules)} permission rule(s) applied to credential {cred_id}")
            except Exception as e:
                effects.append(f"Failed to apply permissions: {e}")

        return "; ".join(effects) if effects else None

    elif req_type == "modify_permissions" and toolkit_id:
        # modify_permissions targets a specific credential via payload.credential_id
        cred_id = payload.get("credential_id")
        rules = payload.get("rules", [])
        if not cred_id:
            return "modify_permissions requires credential_id in payload"
        try:
            await write_credential_permissions(cred_id, rules)
            return f"Permissions updated for credential {cred_id}"
        except Exception as e:
            return f"Failed to update permissions: {e}"

    return None
