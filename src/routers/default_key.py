"""Default API key generation — self-enrollment for agents.

POST /default-api-key/generate

First call (unauthenticated, subnet-restricted):
  - Issues the default tk_xxx key bound to the default toolkit
  - Returns key in plaintext — shown ONCE ONLY, not recoverable
  - Marks instance as claimed; endpoint requires human session on all future calls

Subsequent calls (human session required):
  - Revokes the existing default key
  - Issues a new default key
  - Returns it once

Used by agents during self-enrollment and by humans for key rotation/rescue.
"""
import json
import secrets
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, Response

from src.auth import is_trusted_ip, _client_ip, default_allowed_ips
from src.db import DEFAULT_TOOLKIT_ID, get_db, get_setting, set_setting, setup_state

router = APIRouter(tags=["user"])

_DEFAULT_KEY_LABEL = "Default agent key"
_DEFAULT_KEY_DB_ID = "default_key"


@router.post(
    "/default-api-key/generate",
    status_code=201,
    summary="Generate (or regenerate) the default agent API key",
)
async def generate_default_key(request: Request, response: Response):
    """Issue the default `tk_xxx` agent key bound to the default toolkit.

    **First call** — unauthenticated, subnet-restricted:
    - Available only before the key has been claimed
    - Only accessible from trusted subnets (RFC 1918 + loopback by default;
      configure via `JENTIC_TRUSTED_SUBNETS` env var)
    - Returns the key **once only** — it is not recoverable after this response
    - After this call, the endpoint requires a human session

    **Subsequent calls** — human session required:
    - Revokes the current default key
    - Issues and returns a fresh key

    The key works immediately — you do not need to wait for the admin account
    to be created before using it.
    """
    state = await setup_state()
    is_human = getattr(request.state, "is_human_session", False)
    already_claimed = state["default_key_claimed"]

    if already_claimed and not is_human:
        raise HTTPException(
            401,
            detail={
                "error": "human_session_required",
                "message": "The default key has already been issued. Log in at /user/login to regenerate it.",
                "hint": "POST /user/login with your admin credentials, then retry.",
            },
        )

    if not already_claimed:
        # Subnet restriction on first (unauthenticated) claim
        client_ip = _client_ip(request)
        if not is_trusted_ip(client_ip):
            raise HTTPException(
                403,
                detail={
                    "error": "ip_not_trusted",
                    "message": f"First-time key generation is restricted to trusted subnets. Your IP: {client_ip}",
                    "hint": "Configure JENTIC_TRUSTED_SUBNETS or access from a local network address.",
                },
            )

    # Revoke any existing default key
    async with get_db() as db:
        await db.execute(
            "UPDATE toolkit_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (time.time(), _DEFAULT_KEY_DB_ID),
        )
        await db.commit()

    # Generate new key
    raw_key = "tk_" + secrets.token_hex(16)

    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO toolkit_keys
               (id, toolkit_id, api_key, label, allowed_ips, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (_DEFAULT_KEY_DB_ID, DEFAULT_TOOLKIT_ID, raw_key, _DEFAULT_KEY_LABEL,
             json.dumps(default_allowed_ips()) if default_allowed_ips() else None,
             time.time()),
        )
        await db.commit()

    await set_setting("default_key_claimed", "1")

    setup = await setup_state()
    if not setup["account_created"]:
        import os
        hostname = os.environ.get("JENTIC_PUBLIC_HOSTNAME", "jentic-mini.home.seanblanchfield.com")
        next_step = f"Tell your user to visit {hostname}/user/create to create their admin account."
        setup_url = f"https://{hostname}/user/create"
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
