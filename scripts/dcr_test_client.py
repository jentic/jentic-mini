#!/usr/bin/env python3
"""Local end-to-end test client for the agent Dynamic Client Registration flow.

Walks the full platform-actors agent auth handshake against a locally running
jentic-one instance (combined mode with the `auth` surface enabled):

  1. Generate an Ed25519 keypair and publish the public half as a JWKS.
  2. POST /register            -> receive client_id + registration access token (RAT).
  3. GET  /register/{id}       -> poll status (expects `pending`).
  4. Approve the agent         -> either via the admin API (login + :approve) or,
                                  with --manual-approval, pause for an operator.
                                  Approval invalidates the RAT, so we do NOT poll
                                  GET /register/{id} again afterwards.
  5. Sign a JWT Bearer assertion (alg=EdDSA) and POST /oauth/token to exchange it
     for an opaque access/refresh token pair. This step doubles as the
     activation check: it only succeeds once the agent is active.
  6. (optional) Refresh the pair to demonstrate rotation.

Prerequisites (local run):

    # Postgres fixtures + migrations
    make start-fixtures

    # Combined app with the auth surface and a pinned canonical base URL.
    # config/local.yaml already sets auth.canonical_base_url to http://127.0.0.1:8000.
    JENTIC_CONFIG_FILE=config/local.yaml make start-app

Then, in another shell:

    uv run python scripts/dcr_test_client.py \
        --base-url http://127.0.0.1:8000 \
        --admin-email admin@example.com \
        --admin-password 'your-password'

If you do not have an admin user with `agents:write`/`org:admin`, run with
--manual-approval and flip the status yourself (e.g. via psql) when prompted.
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
import uuid
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
KID = "test-client-key-1"


def _b64url_no_pad(data: bytes) -> str:
    """Base64url-encode without padding, as required for JWK `x` values."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_keypair() -> tuple[Ed25519PrivateKey, dict[str, Any]]:
    """Generate an Ed25519 keypair and return (private_key, public_jwks)."""
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    jwks = {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": _b64url_no_pad(public_raw),
                "kid": KID,
                "use": "sig",
                "alg": "EdDSA",
            }
        ]
    }
    return private_key, jwks


def register_agent(client: httpx.Client, client_name: str, jwks: dict[str, Any]) -> dict[str, Any]:
    resp = client.post(
        "/register",
        json={"client_name": client_name, "jwks": jwks},
    )
    if resp.status_code != 201:
        _fail("register", resp)
    data: dict[str, Any] = resp.json()
    print(f"  registered: client_id={data['client_id']} status={data['status']}")
    return data


def poll_status(client: httpx.Client, agent_id: str, rat: str) -> str:
    resp = client.get(
        f"/register/{agent_id}",
        headers={"Authorization": f"Bearer {rat}"},
    )
    if resp.status_code != 200:
        _fail("poll", resp)
    status: str = resp.json()["status"]
    return status


def admin_login(client: httpx.Client, email: str, password: str) -> str:
    resp = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        _fail("admin login", resp)
    token: str = resp.json()["access_token"]
    print("  admin login: ok")
    return token


def approve_agent(client: httpx.Client, agent_id: str, admin_token: str) -> None:
    resp = client.post(
        f"/agents/{agent_id}:approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if resp.status_code != 200:
        _fail("approve", resp)
    print(f"  approved: status={resp.json().get('status')}")


def build_assertion(private_key: Ed25519PrivateKey, agent_id: str, audience: str) -> str:
    """Sign a short-lived JWT Bearer assertion for grant_type=jwt-bearer."""
    now = int(time.time())
    claims = {
        "iss": agent_id,
        "sub": agent_id,
        "aud": audience,
        "iat": now,
        "exp": now + 120,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, private_key, algorithm="EdDSA", headers={"kid": KID})


def exchange_assertion(client: httpx.Client, assertion: str) -> httpx.Response:
    """POST a JWT Bearer assertion to the token endpoint and return the raw response."""
    return client.post(
        "/oauth/token",
        json={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
    )


def exchange_with_activation_wait(
    client: httpx.Client,
    private_key: Ed25519PrivateKey,
    agent_id: str,
    audience: str,
    *,
    retries: int = 0,
    retry_delay: float = 1.0,
) -> dict[str, Any]:
    """Exchange a JWT Bearer assertion for tokens, waiting for activation.

    The token endpoint returns `400 invalid_grant` while the agent is still
    pending. We retry with a *fresh* assertion each attempt: each assertion is
    short-lived (~120s) and carries a unique jti, so reissuing avoids both
    expiry and the server-side jti replay cache. A 400 is the only retryable
    status; any other failure aborts immediately.
    """
    attempt = 0
    while True:
        assertion = build_assertion(private_key, agent_id, audience)
        resp = exchange_assertion(client, assertion)
        if resp.status_code == 200:
            break
        if resp.status_code != 400 or attempt >= retries:
            _fail("token exchange", resp)
        attempt += 1
        time.sleep(retry_delay)
    data: dict[str, Any] = resp.json()
    print(
        f"  tokens: access={_short(data['access_token'])} "
        f"refresh={_short(data['refresh_token'])} expires_in={data.get('expires_in')}"
    )
    return data


def refresh_pair(client: httpx.Client, refresh_token: str) -> dict[str, Any]:
    resp = client.post(
        "/oauth/token",
        json={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    if resp.status_code != 200:
        _fail("refresh", resp)
    data: dict[str, Any] = resp.json()
    print(
        f"  refreshed: access={_short(data['access_token'])} "
        f"refresh={_short(data['refresh_token'])}"
    )
    return data


def _short(token: str) -> str:
    return f"{token[:12]}...{token[-4:]}" if len(token) > 20 else token


def _fail(step: str, resp: httpx.Response) -> None:
    print(f"\nFAILED at '{step}': HTTP {resp.status_code}", file=sys.stderr)
    print(resp.text, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--client-name", default="dcr-test-client")
    parser.add_argument("--admin-email", default=None)
    parser.add_argument("--admin-password", default=None)
    parser.add_argument(
        "--manual-approval",
        action="store_true",
        help="Pause for an operator to approve out-of-band instead of using the admin API.",
    )
    parser.add_argument(
        "--poll-attempts", type=int, default=30, help="Max status polls after approval."
    )
    parser.add_argument(
        "--skip-refresh", action="store_true", help="Skip the refresh-rotation demo step."
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    audience = f"{base_url}/oauth/token"

    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        print("1. generating Ed25519 keypair + JWKS")
        private_key, jwks = generate_keypair()

        print("2. registering agent")
        reg = register_agent(client, args.client_name, jwks)
        agent_id = reg["client_id"]
        rat = reg["registration_access_token"]

        print("3. polling status (pre-approval)")
        status = poll_status(client, agent_id, rat)
        print(f"  status={status}")

        print("4. approving agent")
        if args.manual_approval:
            input(f"  >> Approve agent {agent_id} out-of-band, then press Enter to continue...")
        elif args.admin_email and args.admin_password:
            admin_token = admin_login(client, args.admin_email, args.admin_password)
            approve_agent(client, agent_id, admin_token)
        else:
            print(
                "  no --admin-email/--admin-password and no --manual-approval; "
                "cannot approve. Re-run with credentials or --manual-approval.",
                file=sys.stderr,
            )
            sys.exit(2)

        print("5. exchanging JWT assertion for tokens")
        # NOTE: we deliberately do not re-poll GET /register/{id} here. On
        # approval the registration access token (RAT) is invalidated by
        # design (RFC 7592 management credential is single-purpose), so a
        # post-approval status poll would 401. Instead we let the token
        # exchange itself confirm activation: it only succeeds once the agent
        # is active. For the manual path we retry briefly to absorb the lag
        # between resuming and the out-of-band approval landing.
        retries = args.poll_attempts if args.manual_approval else 0
        tokens = exchange_with_activation_wait(
            client, private_key, agent_id, audience, retries=retries
        )

        if not args.skip_refresh:
            print("6. refreshing token pair")
            refresh_pair(client, tokens["refresh_token"])

        print("\nDONE: full DCR -> approval -> JWT Bearer -> token flow succeeded.")


if __name__ == "__main__":
    main()
