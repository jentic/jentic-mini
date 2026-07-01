"""Integration tests for SecurityScheme and SecuritySchemeFlow ORM models."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.security_schemes import SecurityScheme, SecuritySchemeFlow
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_security_scheme_and_flow_round_trip(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """SecurityScheme with flows loads eagerly via selectin strategy."""
    api = Api(vendor="oauth-provider.com", name="auth", version="v2")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev = ApiRevision(api_id=api_id)

    async with registry_db.session() as session:
        session.add(rev)
        await session.commit()
        rev_id = rev.id

    scheme = SecurityScheme(
        revision_id=rev_id,
        name="oauth2",
        type="oauth2",
        description="OAuth 2.0 authentication",
        raw_scheme={"type": "oauth2", "flows": {}},
    )

    async with registry_db.session() as session:
        session.add(scheme)
        await session.commit()
        scheme_id = scheme.id

    flow = SecuritySchemeFlow(
        security_scheme_id=scheme_id,
        flow_type="authorizationCode",
        authorization_url="https://auth.example.com/authorize",
        token_url="https://auth.example.com/token",
        refresh_url="https://auth.example.com/refresh",
        scopes={"read": "Read access", "write": "Write access"},
        raw_flow={
            "authorizationUrl": "https://auth.example.com/authorize",
            "tokenUrl": "https://auth.example.com/token",
        },
    )

    async with registry_db.session() as session:
        session.add(flow)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(SecurityScheme).where(SecurityScheme.id == scheme_id))
        loaded = result.scalar_one()

        assert loaded.name == "oauth2"
        assert loaded.type == "oauth2"
        assert loaded.description == "OAuth 2.0 authentication"
        assert loaded.raw_scheme == {"type": "oauth2", "flows": {}}
        assert len(loaded.flows) == 1
        assert loaded.flows[0].flow_type == "authorizationCode"
        assert loaded.flows[0].authorization_url == "https://auth.example.com/authorize"
        assert loaded.flows[0].token_url == "https://auth.example.com/token"
        assert loaded.flows[0].scopes == {"read": "Read access", "write": "Write access"}
