"""Translate ORM security schemes into consumer-facing auth instructions."""

from __future__ import annotations

from jentic_one.registry.core.schema.security_schemes import SecurityScheme, SecuritySchemeFlow
from jentic_one.registry.services.inspect.models import AuthInstruction


def translate_security_schemes(schemes: list[SecurityScheme]) -> list[AuthInstruction]:
    """Convert a list of ORM SecurityScheme objects to AuthInstruction models."""
    result: list[AuthInstruction] = []
    for scheme in schemes:
        if scheme.type == "oauth2":
            result.append(_translate_oauth2(scheme))
        elif scheme.type == "apiKey":
            result.append(_translate_api_key(scheme))
        elif scheme.type == "http":
            result.append(_translate_http(scheme))
        elif scheme.type == "openIdConnect":
            result.append(_translate_open_id_connect(scheme))
        else:
            result.append(AuthInstruction(type=scheme.type))
    return result


def _translate_oauth2(scheme: SecurityScheme) -> AuthInstruction:
    flows: list[dict[str, object]] = []
    for flow in scheme.flows:
        flows.append(_flow_to_dict(flow))
    return AuthInstruction(type="oauth2", flows=flows if flows else None)


def _translate_api_key(scheme: SecurityScheme) -> AuthInstruction:
    return AuthInstruction(
        type="apiKey",
        in_location=scheme.in_location,
        param_name=scheme.param_name,
    )


def _translate_http(scheme: SecurityScheme) -> AuthInstruction:
    return AuthInstruction(
        type="http",
        scheme=scheme.scheme,
        bearer_format=scheme.bearer_format,
    )


def _translate_open_id_connect(scheme: SecurityScheme) -> AuthInstruction:
    return AuthInstruction(
        type="openIdConnect",
        open_id_connect_url=scheme.open_id_connect_url,
    )


def _flow_to_dict(flow: SecuritySchemeFlow) -> dict[str, object]:
    result: dict[str, object] = {"flow_type": flow.flow_type}
    if flow.authorization_url:
        result["authorization_url"] = flow.authorization_url
    if flow.token_url:
        result["token_url"] = flow.token_url
    if flow.refresh_url:
        result["refresh_url"] = flow.refresh_url
    if flow.scopes:
        result["scopes"] = flow.scopes
    return result
