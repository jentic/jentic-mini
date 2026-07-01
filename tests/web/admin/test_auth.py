"""Web tests for the admin auth router."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from jentic_one.admin.core.schema.invite_tokens import InviteToken
from jentic_one.admin.core.schema.setup_sentinel import SetupSentinel
from jentic_one.admin.core.schema.user_permission_grants import UserPermissionGrant
from jentic_one.admin.core.schema.user_secrets import UserSecret
from jentic_one.admin.core.schema.users import User
from jentic_one.shared.context import Context

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD

pytestmark = pytest.mark.integration

# Test-only credentials for the create-admin (first-run) flow. Defined once with
# an allowlist pragma so the secrets scanner doesn't flag every call site.
_BOOTSTRAP_PW = "a-strong-passw0rd"  # pragma: allowlist secret
_OTHER_PW = "another-passw0rd"  # pragma: allowlist secret


def test_login_success(unauthed_client: TestClient, admin_user_id: str) -> None:
    resp = unauthed_client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert "must_change_password" in data


def test_login_invalid_credentials(unauthed_client: TestClient, admin_user_id: str) -> None:
    resp = unauthed_client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["type"] == "invalid_credentials"


def test_login_unknown_email(unauthed_client: TestClient) -> None:
    resp = unauthed_client.post(
        "/auth/login", json={"email": "nobody@nowhere.com", "password": "any"}
    )
    assert resp.status_code == 401
    assert resp.json()["type"] == "invalid_credentials"


def test_me_success(authed_client: TestClient) -> None:
    resp = authed_client.get("/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == ADMIN_EMAIL


def test_me_without_token(unauthed_client: TestClient) -> None:
    resp = unauthed_client.get("/users/me")
    assert resp.status_code == 401


def test_change_password_success(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/users/me:change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "new-secure-pw-12chars"},
    )
    # Re-mints the token (must_change_password cleared), so it returns a login
    # body rather than 204 — the client adopts it without a re-login round-trip.
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["must_change_password"] is False

    # Login with new password should work
    resp = authed_client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "new-secure-pw-12chars"}
    )
    assert resp.status_code == 200

    # Restore original password
    authed_client.post(
        "/users/me:change-password",
        json={"current_password": "new-secure-pw-12chars", "new_password": ADMIN_PASSWORD},
    )


def test_change_password_wrong_current(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/users/me:change-password",
        json={"current_password": "wrong", "new_password": "new-secure-pw-12chars"},
    )
    assert resp.status_code == 401


def test_change_password_too_short(authed_client: TestClient) -> None:
    """Password must be at least 12 characters."""
    resp = authed_client.post(
        "/users/me:change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "short"},
    )
    assert resp.status_code == 422


def test_redeem_invite_accepts_new_field_names(unauthed_client: TestClient) -> None:
    """Redeem invite uses invite_token/password fields (not token/new_password)."""
    resp = unauthed_client.post(
        "/users:redeem-invite",
        json={"invite_token": "fake-token", "password": "twelve_chars_p"},
    )
    # 404 because the token doesn't exist — but validates field names are accepted
    assert resp.status_code == 404


def test_redeem_invite_old_field_names_rejected(unauthed_client: TestClient) -> None:
    """Old field names (token, new_password) are rejected with 422."""
    resp = unauthed_client.post(
        "/users:redeem-invite",
        json={"token": "fake-token", "new_password": "twelve_chars_p"},
    )
    assert resp.status_code == 422


def test_redeem_invite_password_min_length(unauthed_client: TestClient) -> None:
    """Password under 12 chars is rejected."""
    resp = unauthed_client.post(
        "/users:redeem-invite",
        json={"invite_token": "fake-token", "password": "short"},
    )
    assert resp.status_code == 422


# ── First-run create-admin (one-time, unauthenticated setup) ───────────────


@pytest.fixture()
async def _empty_users(web_context: Context) -> AsyncGenerator[None, None]:
    """Empty the users table around the test so create-admin is open.

    The create-admin endpoint self-closes once any user exists OR the setup
    sentinel row is present, so the happy path needs both cleared. Clear before
    and after to avoid leaking the bootstrapped admin (or a stale sentinel that
    would force a spurious 410) into sibling tests on the shared DB.
    """

    async def _wipe() -> None:
        async with web_context.admin_db.session() as session:
            await session.execute(delete(InviteToken))
            await session.execute(delete(UserPermissionGrant))
            await session.execute(delete(UserSecret))
            await session.execute(delete(User))
            await session.execute(delete(SetupSentinel))
            await session.commit()

    await _wipe()
    yield
    await _wipe()


def test_create_admin_first_run(unauthed_client: TestClient, _empty_users: None) -> None:
    """First-run setup creates the admin and returns an auto-login token."""
    resp = unauthed_client.post(
        "/users:create-admin",
        json={"email": "founder@test.local", "password": _BOOTSTRAP_PW},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["must_change_password"] is False

    # The returned token authenticates an org:admin session.
    me = unauthed_client.get(
        "/users/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "founder@test.local"


def test_create_admin_self_closes(unauthed_client: TestClient, _empty_users: None) -> None:
    """A second create-admin (after the first user exists) is rejected 410."""
    first = unauthed_client.post(
        "/users:create-admin",
        json={"email": "first@test.local", "password": _BOOTSTRAP_PW},
    )
    assert first.status_code == 200

    second = unauthed_client.post(
        "/users:create-admin",
        json={"email": "second@test.local", "password": _OTHER_PW},
    )
    assert second.status_code == 410
    assert second.json()["type"] == "setup_already_complete"


def test_create_admin_short_password(unauthed_client: TestClient, _empty_users: None) -> None:
    """Password under 12 chars is rejected by request validation (422).

    Use an 11-char boundary value (not an obviously-tiny "short") and assert the
    error specifically targets the ``password`` field, so this proves the 12-char
    rule fired — not just that *some* unrelated validation failed.
    """
    resp = unauthed_client.post(
        "/users:create-admin",
        json={"email": "founder@test.local", "password": "01234567890"},  # 11 chars
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any(err["loc"][-1] == "password" for err in detail), detail
