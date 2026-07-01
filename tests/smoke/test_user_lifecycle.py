"""Smoke tests for user creation, invite redemption, and access management."""

from __future__ import annotations

import uuid

import pytest

from tests.smoke.conftest import SmokeUser, authed_request


@pytest.mark.smoke
def test_create_and_redeem_user(base_url: str, admin_token: str) -> None:
    """Create a user via admin, redeem the invite, and verify login works."""
    email = f"smoke-lifecycle-{uuid.uuid4().hex[:8]}@test.local"
    password = "SmokeLifecycle123!"

    create_body, status = authed_request(
        f"{base_url}/users",
        method="POST",
        token=admin_token,
        body={"email": email, "first_name": "Life", "last_name": "Cycle"},
    )
    assert status == 201
    assert isinstance(create_body, dict)
    user_id = create_body["user"]["id"]
    invite_token = create_body["invite_token"]

    try:
        redeem_body, redeem_status = authed_request(
            f"{base_url}/users:redeem-invite",
            method="POST",
            body={"invite_token": invite_token, "password": password},
        )
        assert redeem_status == 200
        assert isinstance(redeem_body, dict)
        assert "access_token" in redeem_body
    finally:
        authed_request(f"{base_url}/users/{user_id}", method="DELETE", token=admin_token)


@pytest.mark.smoke
def test_get_current_user(base_url: str, test_user: SmokeUser) -> None:
    """Authenticated user can fetch their own profile with expected permissions."""
    body, status = authed_request(f"{base_url}/users/me", token=test_user.token)
    assert status == 200
    assert isinstance(body, dict)
    assert body["email"] == test_user.email
    assert "permissions" in body


@pytest.mark.smoke
def test_list_users(base_url: str, admin_token: str) -> None:
    """Admin can list users and response is paginated."""
    body, status = authed_request(f"{base_url}/users", token=admin_token)
    assert status == 200
    assert isinstance(body, dict)
    assert "data" in body
    assert len(body["data"]) >= 1
    assert "has_more" in body


@pytest.mark.smoke
def test_disable_and_enable_user(base_url: str, admin_token: str) -> None:
    """Disabling a user blocks login; re-enabling restores access."""
    email = f"smoke-disable-{uuid.uuid4().hex[:8]}@test.local"
    password = "SmokeDisable123!"

    create_body, _ = authed_request(
        f"{base_url}/users",
        method="POST",
        token=admin_token,
        body={"email": email, "first_name": "Dis", "last_name": "Able"},
    )
    assert isinstance(create_body, dict)
    user_id = create_body["user"]["id"]
    invite_token = create_body["invite_token"]

    try:
        authed_request(
            f"{base_url}/users:redeem-invite",
            method="POST",
            body={"invite_token": invite_token, "password": password},
        )

        _, disable_status = authed_request(
            f"{base_url}/users/{user_id}:disable",
            method="POST",
            token=admin_token,
        )
        assert disable_status == 204

        _, login_status = authed_request(
            f"{base_url}/auth/login",
            method="POST",
            body={"email": email, "password": password},
        )
        assert login_status == 401

        _, enable_status = authed_request(
            f"{base_url}/users/{user_id}:enable",
            method="POST",
            token=admin_token,
        )
        assert enable_status == 204

        login_body, login_status = authed_request(
            f"{base_url}/auth/login",
            method="POST",
            body={"email": email, "password": password},
        )
        assert login_status == 200
        assert isinstance(login_body, dict)
        assert "access_token" in login_body
    finally:
        authed_request(f"{base_url}/users/{user_id}", method="DELETE", token=admin_token)
