"""Integration tests for OAuth-token expiry-candidate selection and marking.

Exercises ``OAuthTokenRepository.list_expiry_candidates`` /
``mark_expiry_event_emitted`` against real PostgreSQL — covering the new
``expiring_soon_event_at`` / ``expired_event_at`` marker columns added for the
credential-expiry scanner.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from jentic_one.control.core.schema.credentials import Credential
from jentic_one.control.core.schema.oauth_tokens import OAuthToken
from jentic_one.control.repos.oauth_token_repo import OAuthTokenRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with control_db.session() as session:
        await session.execute(delete(OAuthToken))
        await session.execute(delete(Credential))
        await session.commit()
    yield
    async with control_db.session() as session:
        await session.execute(delete(OAuthToken))
        await session.execute(delete(Credential))
        await session.commit()


async def _seed(
    control_db: DatabaseSession,
    *,
    credential_id: str,
    expires_at: datetime | None,
    revoked: bool = False,
) -> None:
    async with control_db.transaction() as session:
        session.add(
            Credential(
                id=credential_id,
                type="oauth2",
                name=f"cred-{credential_id}",
                api_vendor="stripe",
                provider="direct_oauth2",
            )
        )
        await session.flush()
        session.add(
            OAuthToken(
                id=f"oat_{credential_id}",
                credential_id=credential_id,
                encrypted_access_token="enc:at",
                expires_at=expires_at,
                revoked_at=datetime.now(UTC) if revoked else None,
                created_by="usr_test",
            )
        )


async def test_candidate_query_selects_each_state(control_db: DatabaseSession, clean: None) -> None:
    now = datetime.now(UTC)
    window_end = now + timedelta(hours=72)

    await _seed(control_db, credential_id="cred_expired", expires_at=now - timedelta(hours=1))
    await _seed(control_db, credential_id="cred_soon", expires_at=now + timedelta(hours=24))
    await _seed(control_db, credential_id="cred_far", expires_at=now + timedelta(days=30))
    await _seed(control_db, credential_id="cred_noexp", expires_at=None)
    await _seed(
        control_db,
        credential_id="cred_revoked",
        expires_at=now - timedelta(hours=1),
        revoked=True,
    )

    async with control_db.transaction() as session:
        candidates = await OAuthTokenRepository.list_expiry_candidates(
            session, now=now, window_end=window_end
        )
        selected = {c.credential_id for c in candidates}

    assert selected == {"cred_expired", "cred_soon"}


async def test_marking_excludes_from_subsequent_sweeps(
    control_db: DatabaseSession, clean: None
) -> None:
    now = datetime.now(UTC)
    window_end = now + timedelta(hours=72)
    await _seed(control_db, credential_id="cred_soon", expires_at=now + timedelta(hours=24))

    async with control_db.transaction() as session:
        candidates = await OAuthTokenRepository.list_expiry_candidates(
            session, now=now, window_end=window_end
        )
        assert len(candidates) == 1
        await OAuthTokenRepository.mark_expiry_event_emitted(
            session, candidates[0], kind="expiring_soon", at=now
        )

    async with control_db.transaction() as session:
        candidates = await OAuthTokenRepository.list_expiry_candidates(
            session, now=now, window_end=window_end
        )
        assert candidates == []

    async with control_db.session() as session:
        token = await session.get(OAuthToken, "oat_cred_soon")
        assert token is not None
        assert token.expiring_soon_event_at is not None
        assert token.expired_event_at is None
