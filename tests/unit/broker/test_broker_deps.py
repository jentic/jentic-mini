"""Unit tests for broker web deps — token validation + execute-scope enforcement.

Toolkit *binding* enforcement moved out of ``deps.py`` into ``select_toolkit``
(handler-side, after discovery) in §03 — see ``test_toolkit_select.py``. These
tests cover only what the dependency still owns: authenticate + require the
execute scope.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.testclient import TestClient
from jentic.problem_details import ProblemDetailException, problem_detail_exception_handler

from jentic_one.broker.core.token_validation import CachedTokenValidator
from jentic_one.broker.services.auth import DualTokenValidator
from jentic_one.broker.web.deps import RequireToolkitAccess
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.models import ActorType
from jentic_one.shared.scopes import BROKER_EXECUTE_SCOPE


def _make_identity(
    *,
    sub: str = "agnt_test1",
    actor_type: ActorType = ActorType.AGENT,
    permissions: list[str] | None = None,
    active: bool = True,
) -> Identity:
    return Identity(
        sub=sub,
        actor_type=actor_type,
        permissions=permissions or [BROKER_EXECUTE_SCOPE],
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        active=active,
    )


_SENTINEL = object()


def _create_test_app(resolver_return: Identity | None | object = _SENTINEL) -> TestClient:
    """Build a test client with a mocked opaque-token resolver behind the dual validator."""
    router = APIRouter()

    @router.post("/execute")
    async def execute(request: Request, _identity: RequireToolkitAccess) -> Response:
        return Response(content="ok", status_code=200)

    app = FastAPI()
    app.add_exception_handler(ProblemDetailException, problem_detail_exception_handler)  # type: ignore[arg-type]
    app.include_router(router)

    effective_return = _make_identity() if resolver_return is _SENTINEL else resolver_return
    mock_resolver = AsyncMock()
    mock_resolver.resolve_access_token = AsyncMock(return_value=effective_return)
    opaque = CachedTokenValidator(resolver=mock_resolver, cache_ttl_seconds=60.0)
    app.state.broker_token_validator = DualTokenValidator(opaque=opaque, jwt=None)

    return TestClient(app)


def test_returns_200_with_valid_token_and_scope() -> None:
    client = _create_test_app()
    resp = client.post("/execute", headers={"Authorization": "Bearer at_valid"})
    assert resp.status_code == 200


def test_returns_401_without_authorization_header() -> None:
    client = _create_test_app()
    resp = client.post("/execute")
    assert resp.status_code == 401


def test_returns_401_with_invalid_token() -> None:
    client = _create_test_app(resolver_return=None)
    resp = client.post("/execute", headers={"Authorization": "Bearer at_invalid"})
    assert resp.status_code == 401


def test_returns_401_with_inactive_token() -> None:
    client = _create_test_app(resolver_return=_make_identity(active=False))
    resp = client.post("/execute", headers={"Authorization": "Bearer at_revoked"})
    assert resp.status_code == 401


def test_returns_403_with_insufficient_scope() -> None:
    client = _create_test_app(resolver_return=_make_identity(permissions=["read:only"]))
    resp = client.post("/execute", headers={"Authorization": "Bearer at_limited"})
    assert resp.status_code == 403
    assert resp.json()["type"] == "insufficient_scope"
