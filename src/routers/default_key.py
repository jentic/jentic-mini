"""Default toolkit API key rotation (human only).

POST /default-api-key/generate

New instances no longer receive an automatic default `tk_xxx` key; giving that key to an agent
as the primary onboarding path is deprecated in favor of OAuth DCR (`POST /register`, etc.).

**When a default key was issued in the past** (`default_key_claimed`):
  - Human session required to rotate
  - Revokes the existing default key and issues a new one

Humans can still create additional toolkit keys from the UI or API for automation and integrations.
"""

import json
import secrets
import time

from fastapi import APIRouter, HTTPException, Request

from src.auth import default_allowed_ips
from src.db import DEFAULT_TOOLKIT_ID, get_db, set_setting, setup_state
from src.utils import build_absolute_url


router = APIRouter(tags=["user"])

_DEFAULT_KEY_LABEL = "Default agent key"
_DEFAULT_KEY_DB_ID = "default_key"


@router.post(
    "/default-api-key/generate",
    status_code=201,
    summary="Generate (or regenerate) the default toolkit API key",
)
async def generate_default_key(request: Request):
    """Rotate the default `tk_xxx` key for the default toolkit (human session only).

    Only available when a default key was created in the past. New instances use agent identity
    (OAuth DCR) for agent onboarding; toolkit keys remain valid for other uses.
    """
    state = await setup_state()
    is_human = getattr(request.state, "is_human_session", False)
    already_claimed = state["default_key_claimed"]

    if not already_claimed:
        raise HTTPException(
            410,
            detail={
                "error": "default_toolkit_key_disabled",
                "message": "Default toolkit API keys are not issued for new instances.",
                "hint": (
                    "Use GET /.well-known/oauth-authorization-server and POST /register "
                    "for agent identity. Humans may create additional toolkit keys from the UI."
                ),
            },
        )

    if not is_human:
        raise HTTPException(
            401,
            detail={
                "error": "human_session_required",
                "message": "Regenerating the default key requires a human session.",
                "hint": "POST /user/login with your admin credentials, then retry.",
            },
        )

    async with get_db() as db:
        await db.execute(
            "UPDATE toolkit_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (time.time(), _DEFAULT_KEY_DB_ID),
        )
        await db.commit()

    raw_key = "tk_" + secrets.token_hex(16)

    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO toolkit_keys
               (id, toolkit_id, api_key, label, allowed_ips, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                _DEFAULT_KEY_DB_ID,
                DEFAULT_TOOLKIT_ID,
                raw_key,
                _DEFAULT_KEY_LABEL,
                json.dumps(default_allowed_ips()) if default_allowed_ips() else None,
                time.time(),
            ),
        )
        await db.commit()

    await set_setting("default_key_claimed", "1")

    setup = await setup_state()
    if not setup["account_created"]:
        setup_url = build_absolute_url(request, "/user/create")
        next_step = f"Tell your user to visit {setup_url} to create their admin account."
    else:
        next_step = "Key ready. Use it as X-Jentic-API-Key on all agent requests."
        setup_url = None

    result = {
        "key": raw_key,
        "toolkit_id": DEFAULT_TOOLKIT_ID,
        "label": _DEFAULT_KEY_LABEL,
        "message": "This key will not be shown again. Store it securely in your agent configuration.",
        "next_step": next_step,
    }
    if setup_url:
        result["setup_url"] = setup_url

    return result
