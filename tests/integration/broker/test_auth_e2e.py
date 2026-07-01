"""Integration tests for the broker's dual-token validation against a live admin DB.

Seeds an opaque ``access_tokens`` row and asserts the ``DualTokenValidator``:
  - resolves the opaque token via the in-process admin-DB resolver, and
  - validates a short-TTL self-contained signed JWT **without** any DB lookup.

This exercises the §03 wiring (``install_broker_auth`` builds the same dispatcher)
end-to-end through the real ``InProcessTokenResolver``.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.access_tokens import AccessToken
from jentic_one.admin.repos.access_token_repo import AccessTokenRepository
from jentic_one.broker.core.token_validation import CachedTokenValidator
from jentic_one.broker.repos.token_resolver import InProcessTokenResolver
from jentic_one.broker.services.auth import DualTokenValidator, JwtTokenValidator, JwtVerifier
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.scopes import BROKER_EXECUTE_SCOPE

pytestmark = pytest.mark.integration

_JWT_SECRET = "integration-test-secret-key-32-bytes!!"  # pragma: allowlist secret


@pytest.fixture()
async def clean_access_tokens(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async def _truncate() -> None:
        async with admin_db.session() as session:
            await session.execute(delete(AccessToken))
            await session.commit()

    await _truncate()
    yield
    await _truncate()


def _dual(admin_db: DatabaseSession, *, with_jwt: bool = True) -> DualTokenValidator:
    opaque = CachedTokenValidator(resolver=InProcessTokenResolver(admin_db))
    jwt_validator = (
        JwtTokenValidator(verifier=JwtVerifier(secret=_JWT_SECRET)) if with_jwt else None
    )
    return DualTokenValidator(opaque=opaque, jwt=jwt_validator)


async def _seed_opaque_token(admin_db: DatabaseSession, *, plaintext: str) -> None:
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    async with admin_db.session() as session:
        await AccessTokenRepository.create(
            session,
            token_hash=token_hash,
            actor_id="agnt_opaque",
            actor_type="agent",
            scopes=[BROKER_EXECUTE_SCOPE],
            token_family_id="fam_test",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            created_by="agnt_opaque",
        )
        await session.commit()


async def test_opaque_token_resolves_via_db(
    admin_db: DatabaseSession, clean_access_tokens: None
) -> None:
    await _seed_opaque_token(admin_db, plaintext="at_live_opaque")

    resolved = await _dual(admin_db).validate("at_live_opaque")

    assert resolved.sub == "agnt_opaque"
    assert BROKER_EXECUTE_SCOPE in resolved.permissions


async def test_signed_jwt_validates_without_db_lookup(
    admin_db: DatabaseSession, clean_access_tokens: None
) -> None:
    # No row seeded — a JWT must validate purely by signature.
    exp = int((datetime.now(UTC) + timedelta(minutes=2)).timestamp())
    token = jwt.encode(
        {"sub": "agnt_jwt", "exp": exp, "scopes": [BROKER_EXECUTE_SCOPE]},
        _JWT_SECRET,
        algorithm="HS256",
    )

    resolved = await _dual(admin_db).validate(token)

    assert resolved.sub == "agnt_jwt"
    assert resolved.permissions == [BROKER_EXECUTE_SCOPE]


async def test_unknown_opaque_token_is_rejected(
    admin_db: DatabaseSession, clean_access_tokens: None
) -> None:
    with pytest.raises(ValueError):
        await _dual(admin_db).validate("at_does_not_exist")
