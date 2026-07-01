"""Integration tests for OAuth token endpoints against real DB."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

from jentic_one.admin.core.schema.access_tokens import AccessToken
from jentic_one.admin.core.schema.actor_scope_grants import ActorScopeGrant
from jentic_one.admin.core.schema.refresh_tokens import RefreshToken
from jentic_one.admin.repos import AccessTokenRepository, ActorScopeGrantRepository
from jentic_one.auth.services.errors import InvalidGrantError
from jentic_one.auth.services.token_service import TokenService, _hash_token
from jentic_one.auth.web.routers.oauth import token_endpoint
from jentic_one.auth.web.schemas.oauth import TokenRequest
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.db.errors import DatabaseUnavailableError
from jentic_one.shared.models import ActorType

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_tokens(integration_context: Context) -> AsyncGenerator[None, None]:
    async with integration_context.admin_db.session() as session:
        await session.execute(delete(AccessToken))
        await session.execute(delete(RefreshToken))
        await session.execute(delete(ActorScopeGrant))
        await session.commit()
    yield
    async with integration_context.admin_db.session() as session:
        await session.execute(delete(AccessToken))
        await session.execute(delete(RefreshToken))
        await session.execute(delete(ActorScopeGrant))
        await session.commit()


@pytest.fixture()
def token_service(integration_context: Context) -> TokenService:
    return TokenService(integration_context)


async def test_issue_pair_lifecycle(token_service: TokenService, clean_tokens: None) -> None:
    """Full lifecycle: issue -> introspect (active) -> revoke -> introspect (inactive)."""
    access, refresh = await token_service.issue_pair("usr_test1", ActorType.USER, ["read", "write"])

    assert access.startswith("at_")
    assert refresh.startswith("rt_")

    result = await token_service.introspect(access)
    assert result["active"] is True
    assert result["sub"] == "usr_test1"
    assert result["scope"] == "read write"

    await token_service.revoke(access, identity=Identity(sub="usr_test1", email="test@local"))

    result = await token_service.introspect(access)
    assert result["active"] is False


async def test_refresh_rotation(token_service: TokenService, clean_tokens: None) -> None:
    """Issue -> refresh -> verify new pair works, old is consumed."""
    access1, refresh1 = await token_service.issue_pair("usr_test2", ActorType.USER, ["read"])

    access2, refresh2 = await token_service.refresh(refresh1)

    assert access2.startswith("at_")
    assert refresh2.startswith("rt_")
    assert access2 != access1
    assert refresh2 != refresh1

    result = await token_service.introspect(access2)
    assert result["active"] is True

    old_rt_result = await token_service.introspect(refresh1)
    assert old_rt_result["active"] is False


async def test_reuse_detection(token_service: TokenService, clean_tokens: None) -> None:
    """Issue -> refresh -> replay old refresh -> entire family revoked."""
    _access1, refresh1 = await token_service.issue_pair("usr_test3", ActorType.USER, ["read"])

    access2, _refresh2 = await token_service.refresh(refresh1)

    with pytest.raises(InvalidGrantError, match="reuse detected"):
        await token_service.refresh(refresh1)

    result = await token_service.introspect(access2)
    assert result["active"] is False


async def test_introspect_expired_returns_inactive(
    integration_context: Context, clean_tokens: None
) -> None:
    """Expired token introspection returns inactive."""
    async with integration_context.admin_db.transaction() as session:
        await AccessTokenRepository.create(
            session,
            token_hash=_hash_token("at_expired_test"),
            actor_id="usr_expired",
            actor_type="user",
            scopes=["read"],
            token_family_id="tfam_expired",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_by="usr_test",
            is_ephemeral=False,
        )

    svc = TokenService(integration_context)
    result = await svc.introspect("at_expired_test")
    assert result["active"] is False


async def test_token_endpoint_unsupported_grant_type(
    token_service: TokenService, clean_tokens: None
) -> None:
    """Invalid grant_type raises InvalidGrantError."""
    with pytest.raises(InvalidGrantError, match="unsupported grant_type"):
        body = TokenRequest(grant_type="invalid_grant", refresh_token=None)
        await token_endpoint(body=body, token_svc=token_service)


async def test_invalid_refresh_token(token_service: TokenService, clean_tokens: None) -> None:
    """Attempting to refresh with an invalid token raises InvalidGrantError."""
    with pytest.raises(InvalidGrantError, match="not found"):
        await token_service.refresh("rt_invalid_doesnotexist")


async def test_resolve_access_token(
    token_service: TokenService, integration_context: Context, clean_tokens: None
) -> None:
    """resolve_access_token returns an Identity whose scopes reflect *live* grants.

    Long-lived agent tokens (an access+refresh pair) resolve scopes from the
    actor's current ``ActorScopeGrant`` rows, so a scope change is reflected
    immediately. Seed the grant that a real ``issue_pair`` would have derived
    from.
    """
    async with integration_context.admin_db.session() as session:
        await ActorScopeGrantRepository.grant(
            session,
            actor_id="agnt_resolve1",
            actor_type=ActorType.AGENT,
            scope="execute",
            granted_by="usr_test",
            created_by="usr_test",
        )
        await session.commit()

    access, _refresh = await token_service.issue_pair("agnt_resolve1", ActorType.AGENT, ["execute"])

    resolved = await token_service.resolve_access_token(access)
    assert resolved is not None
    assert resolved.active is True
    assert resolved.sub == "agnt_resolve1"
    assert resolved.actor_type == "agent"
    assert resolved.permissions == ["execute"]


async def test_resolve_reflects_scope_grant_without_remint(
    token_service: TokenService, integration_context: Context, clean_tokens: None
) -> None:
    """Regression for #531: adding a scope grant takes effect on the *existing*
    token pair — no re-mint required."""
    async with integration_context.admin_db.session() as session:
        await ActorScopeGrantRepository.grant(
            session,
            actor_id="agnt_scope",
            actor_type=ActorType.AGENT,
            scope="apis:read",
            granted_by="usr_owner",
            created_by="usr_owner",
        )
        await session.commit()

    access, _refresh = await token_service.issue_pair("agnt_scope", ActorType.AGENT, ["apis:read"])
    resolved = await token_service.resolve_access_token(access)
    assert resolved is not None
    assert resolved.permissions == ["apis:read"]

    # Owner grants apis:write after the token was minted.
    async with integration_context.admin_db.session() as session:
        await ActorScopeGrantRepository.grant(
            session,
            actor_id="agnt_scope",
            actor_type=ActorType.AGENT,
            scope="apis:write",
            granted_by="usr_owner",
            created_by="usr_owner",
        )
        await session.commit()

    # The same (unchanged) access token now resolves the new scope.
    resolved = await token_service.resolve_access_token(access)
    assert resolved is not None
    assert resolved.permissions == ["apis:read", "apis:write"]


async def test_resolve_reflects_scope_revocation_without_remint(
    token_service: TokenService, integration_context: Context, clean_tokens: None
) -> None:
    """Revoking a scope also takes effect on the existing token pair immediately."""
    async with integration_context.admin_db.session() as session:
        for scope in ("apis:read", "apis:write"):
            await ActorScopeGrantRepository.grant(
                session,
                actor_id="agnt_revoke",
                actor_type=ActorType.AGENT,
                scope=scope,
                granted_by="usr_owner",
                created_by="usr_owner",
            )
        await session.commit()

    access, _refresh = await token_service.issue_pair(
        "agnt_revoke", ActorType.AGENT, ["apis:read", "apis:write"]
    )

    async with integration_context.admin_db.session() as session:
        await ActorScopeGrantRepository.revoke(session, actor_id="agnt_revoke", scope="apis:write")
        await session.commit()

    resolved = await token_service.resolve_access_token(access)
    assert resolved is not None
    assert resolved.permissions == ["apis:read"]


async def test_issue_pair_transient_lock_exhausted_raises_db_unavailable(
    token_service: TokenService, clean_tokens: None
) -> None:
    """A transient OperationalError that outlasts the retry budget surfaces as 503-mapped error.

    Drives the real ``issue_pair`` write through ``run_in_transaction`` against the
    real admin DB; ``AccessTokenRepository.create`` is forced to raise a transient
    ``OperationalError`` (the same class SQLite raises on ``database is locked``).
    After retries are exhausted it must raise ``DatabaseUnavailableError`` — the
    web layer maps that to HTTP 503 ``database_unavailable`` (see
    tests/unit/auth/web/test_oauth_db_unavailable.py), not a bare 500.
    """

    def _raise_locked(*_args: object, **_kwargs: object) -> None:
        raise OperationalError("INSERT INTO access_tokens", {}, Exception("database is locked"))

    with (
        patch.object(AccessTokenRepository, "create", side_effect=_raise_locked),
        pytest.raises(DatabaseUnavailableError),
    ):
        await token_service.issue_pair("usr_locked", ActorType.USER, ["read"])


async def test_issue_pair_transient_lock_then_success(
    token_service: TokenService, clean_tokens: None
) -> None:
    """A transient lock on the first attempt is retried and the mint then succeeds."""
    real_create = AccessTokenRepository.create
    calls = {"n": 0}

    async def _flaky_create(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("INSERT INTO access_tokens", {}, Exception("database is locked"))
        return await real_create(*args, **kwargs)  # type: ignore[arg-type]

    with patch.object(AccessTokenRepository, "create", side_effect=_flaky_create):
        access, refresh = await token_service.issue_pair("usr_retry", ActorType.USER, ["read"])

    assert access.startswith("at_")
    assert refresh.startswith("rt_")
    assert calls["n"] >= 2
    result = await token_service.introspect(access)
    assert result["active"] is True


async def test_revoke_refresh_token_revokes_family(
    token_service: TokenService, clean_tokens: None
) -> None:
    """Revoking a refresh token revokes the entire token family."""
    access, refresh = await token_service.issue_pair("usr_fam1", ActorType.USER, ["read"])

    await token_service.revoke(refresh, identity=Identity(sub="usr_fam1", email="test@local"))

    at_result = await token_service.introspect(access)
    assert at_result["active"] is False

    rt_result = await token_service.introspect(refresh)
    assert rt_result["active"] is False
