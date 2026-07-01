"""Unit tests for inspect auth translation."""

from __future__ import annotations

from unittest.mock import MagicMock

from jentic_one.registry.services.inspect.auth import translate_security_schemes


def _make_scheme(
    *,
    type: str = "http",
    scheme: str | None = "bearer",
    bearer_format: str | None = "JWT",
    in_location: str | None = None,
    param_name: str | None = None,
    open_id_connect_url: str | None = None,
    flows: list[object] | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.type = type
    mock.scheme = scheme
    mock.bearer_format = bearer_format
    mock.in_location = in_location
    mock.param_name = param_name
    mock.open_id_connect_url = open_id_connect_url
    mock.flows = flows or []
    return mock


def _make_flow(
    *,
    flow_type: str = "authorizationCode",
    authorization_url: str | None = "https://auth.example.com/authorize",
    token_url: str | None = "https://auth.example.com/token",
    refresh_url: str | None = None,
    scopes: dict[str, str] | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.flow_type = flow_type
    mock.authorization_url = authorization_url
    mock.token_url = token_url
    mock.refresh_url = refresh_url
    mock.scopes = scopes
    return mock


def test_http_scheme() -> None:
    scheme = _make_scheme(type="http", scheme="bearer", bearer_format="JWT")
    result = translate_security_schemes([scheme])
    assert len(result) == 1
    assert result[0].type == "http"
    assert result[0].scheme == "bearer"
    assert result[0].bearer_format == "JWT"


def test_api_key_scheme() -> None:
    scheme = _make_scheme(type="apiKey", in_location="header", param_name="X-API-Key")
    result = translate_security_schemes([scheme])
    assert len(result) == 1
    assert result[0].type == "apiKey"
    assert result[0].in_location == "header"
    assert result[0].param_name == "X-API-Key"


def test_open_id_connect_scheme() -> None:
    scheme = _make_scheme(
        type="openIdConnect",
        open_id_connect_url="https://auth.example.com/.well-known/openid-configuration",
    )
    result = translate_security_schemes([scheme])
    assert len(result) == 1
    assert result[0].type == "openIdConnect"
    assert result[0].open_id_connect_url is not None


def test_oauth2_scheme_with_flows() -> None:
    flow = _make_flow(
        flow_type="authorizationCode",
        authorization_url="https://auth.example.com/authorize",
        token_url="https://auth.example.com/token",
        scopes={"read": "Read access"},
    )
    scheme = _make_scheme(type="oauth2", flows=[flow])
    result = translate_security_schemes([scheme])
    assert len(result) == 1
    assert result[0].type == "oauth2"
    assert result[0].flows is not None
    assert len(result[0].flows) == 1
    assert result[0].flows[0]["flow_type"] == "authorizationCode"


def test_empty_list() -> None:
    result = translate_security_schemes([])
    assert result == []


def test_unknown_type() -> None:
    scheme = _make_scheme(type="mutualTLS")
    result = translate_security_schemes([scheme])
    assert len(result) == 1
    assert result[0].type == "mutualTLS"
