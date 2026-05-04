"""No-auth API passthrough tests — broker should forward without credentials
when an auth_type=none credential is configured, and block when no credential
exists for the host (fail-closed).

Prior to the credential_routes migration, the broker checked the API spec's
securitySchemes to decide whether to require credentials. This was replaced by
a purely route-based model:
  - auth_type=none credential  → forward without injecting auth headers  → 502 (unreachable)
  - no credential for host     → 403 policy_denied (fail-closed)
"""

import asyncio
import os

import aiosqlite
import pytest
from src import vault


NO_AUTH_HOST = "127.0.0.3"
AUTH_HOST = "127.0.0.4"


@pytest.fixture(scope="module")
def registered_apis():
    """Register a no-auth credential for NO_AUTH_HOST; leave AUTH_HOST unconfigured."""

    async def setup():
        db_path = os.environ["DB_PATH"]

        enc = vault.encrypt("")  # no-auth: empty value
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO credentials "
                "(id, label, env_var, encrypted_value, api_id, auth_type) "
                "VALUES (?, ?, ?, ?, ?, 'none')",
                ("no-auth-api-test", "No-Auth API", "NO_AUTH_API_TEST", enc, NO_AUTH_HOST),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                ("no-auth-api-test", NO_AUTH_HOST),
            )
            # Bind credential to the default toolkit so the broker can find it
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) "
                "VALUES ('default', 'no-auth-api-test')",
            )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM credential_routes WHERE credential_id='no-auth-api-test'")
            await db.execute(
                "DELETE FROM toolkit_credentials WHERE credential_id='no-auth-api-test'"
            )
            await db.execute("DELETE FROM credentials WHERE id='no-auth-api-test'")
            await db.commit()

    asyncio.run(teardown())


def test_no_auth_api_forwards_without_credentials(client, agent_key_header, registered_apis):
    """An auth_type=none credential allows broker passthrough without injecting auth.

    The upstream is non-routable so we expect a connection error (502), not a
    credential or policy error.
    """
    resp = client.get(f"/{NO_AUTH_HOST}/get", headers=agent_key_header)
    assert resp.status_code == 502, (
        f"Expected 502 (upstream unreachable), got {resp.status_code}: {resp.text}"
    )


def test_auth_api_requires_credentials(client, agent_key_header, registered_apis):
    """A host with no configured credential returns 403 policy_denied (fail-closed).

    Previously the broker returned 500 CREDENTIAL_LOOKUP_FAILED when it couldn't
    find a scheme in the spec. The route-based model replaces this with a clean
    403: if no credential_routes row exists for the host, the request is denied.
    """
    resp = client.get(f"/{AUTH_HOST}/data", headers=agent_key_header)
    assert resp.status_code == 403, (
        f"Expected 403 policy_denied (no credential for host), got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("error") == "policy_denied", f"Unexpected error code: {body}"
