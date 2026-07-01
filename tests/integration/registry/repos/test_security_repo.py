"""Integration tests for SecurityRepository."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.security_schemes import SecurityScheme, SecuritySchemeFlow
from jentic_one.registry.repos.security_repo import SecurityRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_store_security_schemes_basic(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """store_security_schemes creates scheme entries and returns UUIDs."""
    _, rev = sample_revision
    schemes = {
        "api_key": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }

    async with registry_db.session() as session:
        ids = await SecurityRepository.store_security_schemes(
            session, revision_id=rev.id, schemes=schemes, created_by="usr_test"
        )
        await session.commit()

    assert len(ids) == 1


async def test_store_security_schemes_with_oauth2_flows(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """store_security_schemes creates OAuth2 flows linked to schemes."""
    _, rev = sample_revision
    schemes = {
        "oauth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://auth.example.com/authorize",
                    "tokenUrl": "https://auth.example.com/token",
                    "refreshUrl": "https://auth.example.com/refresh",
                    "scopes": {"read": "Read access", "write": "Write access"},
                },
                "clientCredentials": {
                    "tokenUrl": "https://auth.example.com/token",
                    "scopes": {"admin": "Admin access"},
                },
            },
        }
    }

    async with registry_db.session() as session:
        ids = await SecurityRepository.store_security_schemes(
            session, revision_id=rev.id, schemes=schemes, created_by="usr_test"
        )
        await session.commit()
        scheme_id = ids[0]

    async with registry_db.session() as session:
        result = await session.execute(select(SecurityScheme).where(SecurityScheme.id == scheme_id))
        scheme = result.scalar_one()
        assert scheme.name == "oauth2"
        assert scheme.type == "oauth2"
        assert len(scheme.flows) == 2

        flow_types = {f.flow_type for f in scheme.flows}
        assert flow_types == {"authorizationCode", "clientCredentials"}

        auth_flow = next(f for f in scheme.flows if f.flow_type == "authorizationCode")
        assert auth_flow.authorization_url == "https://auth.example.com/authorize"
        assert auth_flow.token_url == "https://auth.example.com/token"
        assert auth_flow.refresh_url == "https://auth.example.com/refresh"
        assert auth_flow.scopes == {"read": "Read access", "write": "Write access"}


async def test_delete_for_revision_cascades_to_flows(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """delete_for_revision removes schemes and cascades to flows."""
    _, rev = sample_revision
    schemes = {
        "oauth2": {
            "type": "oauth2",
            "flows": {
                "implicit": {
                    "authorizationUrl": "https://auth.example.com/authorize",
                    "scopes": {},
                }
            },
        }
    }

    async with registry_db.session() as session:
        await SecurityRepository.store_security_schemes(
            session, revision_id=rev.id, schemes=schemes, created_by="usr_test"
        )
        await session.commit()

    async with registry_db.session() as session:
        await SecurityRepository.delete_for_revision(session, rev.id)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(
            select(SecurityScheme).where(SecurityScheme.revision_id == rev.id)
        )
        assert result.scalars().all() == []
        result = await session.execute(select(SecuritySchemeFlow))
        assert result.scalars().all() == []


async def test_revision_name_uniqueness(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """(revision_id, name) uniqueness is enforced."""
    _, rev = sample_revision
    schemes = {"bearer": {"type": "http", "scheme": "bearer"}}

    async with registry_db.session() as session:
        await SecurityRepository.store_security_schemes(
            session, revision_id=rev.id, schemes=schemes, created_by="usr_test"
        )
        await session.commit()

    with pytest.raises(IntegrityError):
        async with registry_db.session() as session:
            await SecurityRepository.store_security_schemes(
                session, revision_id=rev.id, schemes=schemes, created_by="usr_test"
            )
            await session.commit()
