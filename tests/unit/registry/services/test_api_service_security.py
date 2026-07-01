"""Unit tests for ApiService.get_security_schemes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.registry.services.api_service import ApiService
from jentic_one.registry.services.errors import ApiNotFoundError, NoCurrentRevisionError


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    mock_session = AsyncMock()
    ctx.registry_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.registry_db.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_flow(
    *,
    flow_type: str = "authorizationCode",
    authorization_url: str | None = "https://auth.example.com/authorize",
    token_url: str | None = "https://auth.example.com/token",
    refresh_url: str | None = None,
    scopes: dict[str, str] | None = None,
) -> MagicMock:
    flow = MagicMock()
    flow.flow_type = flow_type
    flow.authorization_url = authorization_url
    flow.token_url = token_url
    flow.refresh_url = refresh_url
    flow.scopes = scopes
    return flow


def _make_scheme(
    *,
    name: str = "oauth2",
    type_: str = "oauth2",
    scheme: str | None = None,
    bearer_format: str | None = None,
    in_location: str | None = None,
    param_name: str | None = None,
    open_id_connect_url: str | None = None,
    description: str | None = None,
    flows: list[MagicMock] | None = None,
) -> MagicMock:
    s = MagicMock()
    s.name = name
    s.type = type_
    s.scheme = scheme
    s.bearer_format = bearer_format
    s.in_location = in_location
    s.param_name = param_name
    s.open_id_connect_url = open_id_connect_url
    s.description = description
    s.flows = flows or []
    return s


def _make_api(
    *, has_current_revision: bool = True, security_schemes: list[MagicMock] | None = None
) -> MagicMock:
    api = MagicMock()
    api.id = uuid.uuid4()
    if has_current_revision:
        api.current_revision = MagicMock()
        api.current_revision.id = uuid.uuid4()
        api.current_revision.security_schemes = security_schemes or []
    else:
        api.current_revision = None
    return api


@pytest.mark.asyncio
async def test_get_security_schemes_maps_orm_to_response() -> None:
    ctx = _make_ctx()
    flow = _make_flow(scopes={"read": "Read access"})
    scheme = _make_scheme(flows=[flow])
    api = _make_api(security_schemes=[scheme])

    with patch(
        "jentic_one.registry.services.api_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=api,
    ):
        svc = ApiService(ctx)
        result = await svc.get_security_schemes("acme", "pets", "v1")

    assert len(result.data) == 1
    s = result.data[0]
    assert s.name == "oauth2"
    assert s.type == "oauth2"
    assert len(s.flows) == 1
    assert s.flows[0].flow_type == "authorizationCode"
    assert s.flows[0].authorization_url == "https://auth.example.com/authorize"
    assert s.flows[0].scopes == {"read": "Read access"}


@pytest.mark.asyncio
async def test_get_security_schemes_api_not_found() -> None:
    ctx = _make_ctx()

    with patch(
        "jentic_one.registry.services.api_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=None,
    ):
        svc = ApiService(ctx)
        with pytest.raises(ApiNotFoundError):
            await svc.get_security_schemes("acme", "missing", "v1")


@pytest.mark.asyncio
async def test_get_security_schemes_no_current_revision() -> None:
    ctx = _make_ctx()
    api = _make_api(has_current_revision=False)

    with patch(
        "jentic_one.registry.services.api_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=api,
    ):
        svc = ApiService(ctx)
        with pytest.raises(NoCurrentRevisionError):
            await svc.get_security_schemes("acme", "pets", "v1")


@pytest.mark.asyncio
async def test_get_security_schemes_empty_list() -> None:
    ctx = _make_ctx()
    api = _make_api(security_schemes=[])

    with patch(
        "jentic_one.registry.services.api_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=api,
    ):
        svc = ApiService(ctx)
        result = await svc.get_security_schemes("acme", "pets", "v1")

    assert result.data == []


@pytest.mark.asyncio
async def test_get_security_schemes_multiple_types() -> None:
    """Maps multiple scheme types (apiKey, http) correctly."""
    ctx = _make_ctx()
    api_key_scheme = _make_scheme(
        name="api_key", type_="apiKey", in_location="header", param_name="X-API-Key"
    )
    http_scheme = _make_scheme(
        name="bearer_auth", type_="http", scheme="bearer", bearer_format="JWT"
    )
    api = _make_api(security_schemes=[api_key_scheme, http_scheme])

    with patch(
        "jentic_one.registry.services.api_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=api,
    ):
        svc = ApiService(ctx)
        result = await svc.get_security_schemes("acme", "pets", "v1")

    assert len(result.data) == 2
    key_resp = result.data[0]
    assert key_resp.name == "api_key"
    assert key_resp.type == "apiKey"
    assert key_resp.in_location == "header"
    assert key_resp.param_name == "X-API-Key"
    assert key_resp.flows == []

    http_resp = result.data[1]
    assert http_resp.name == "bearer_auth"
    assert http_resp.type == "http"
    assert http_resp.scheme == "bearer"
    assert http_resp.bearer_format == "JWT"
