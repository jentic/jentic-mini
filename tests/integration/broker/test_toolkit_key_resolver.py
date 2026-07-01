"""Integration tests for the ``ToolkitKeyResolver``.

Seeds the control DB (a toolkit + a real ``jntc_live_`` key with its SHA-256
``lookup_hash``), then asserts the resolver maps the plaintext key to a
toolkit-scoped ``Identity`` and rejects revoked keys / inactive toolkits.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.broker.repos.toolkit_key_resolver import ToolkitKeyResolver
from jentic_one.control.core.schema.toolkit_keys import ToolkitKey
from jentic_one.control.core.schema.toolkits import Toolkit
from jentic_one.control.services.toolkits.key_gen import generate_toolkit_key
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import ActorType
from jentic_one.shared.scopes import BROKER_EXECUTE_SCOPE

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_tables(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Truncate the control tables this module touches, before and after."""

    async def _truncate() -> None:
        async with control_db.session() as session:
            await session.execute(delete(ToolkitKey))
            await session.execute(delete(Toolkit))
            await session.commit()

    await _truncate()
    yield
    await _truncate()


async def _seed_toolkit_key(
    control_db: DatabaseSession,
    *,
    toolkit_name: str,
    active: bool = True,
    revoked: bool = False,
) -> tuple[str, str]:
    """Create a toolkit + key; return (toolkit_id, plaintext_key)."""
    plaintext, hashed, preview, lookup = generate_toolkit_key()
    toolkit = Toolkit(name=toolkit_name, active=active)
    async with control_db.session() as session:
        session.add(toolkit)
        await session.flush()
        tk_id = toolkit.id
        session.add(
            ToolkitKey(
                toolkit_id=tk_id,
                hashed_key=hashed,
                key_preview=preview,
                lookup_hash=lookup,
                revoked=revoked,
                created_by="usr_test",
            )
        )
        await session.commit()
    return tk_id, plaintext


async def test_resolves_valid_key_to_toolkit_identity(
    control_db: DatabaseSession, clean_tables: None
) -> None:
    tk_id, plaintext = await _seed_toolkit_key(control_db, toolkit_name="tk-valid")

    resolver = ToolkitKeyResolver(control_db)
    identity = await resolver.resolve(plaintext)

    assert identity is not None
    assert identity.sub == tk_id
    assert identity.actor_type is ActorType.TOOLKIT
    assert identity.permissions == [BROKER_EXECUTE_SCOPE]
    assert identity.active is True


async def test_unknown_key_resolves_to_none(
    control_db: DatabaseSession, clean_tables: None
) -> None:
    await _seed_toolkit_key(control_db, toolkit_name="tk-known")

    resolver = ToolkitKeyResolver(control_db)
    assert await resolver.resolve("jntc_live_does_not_exist") is None


async def test_non_toolkit_prefix_resolves_to_none(
    control_db: DatabaseSession, clean_tables: None
) -> None:
    resolver = ToolkitKeyResolver(control_db)
    assert await resolver.resolve("jak_some_agent_key") is None


async def test_revoked_key_resolves_to_none(
    control_db: DatabaseSession, clean_tables: None
) -> None:
    _tk_id, plaintext = await _seed_toolkit_key(control_db, toolkit_name="tk-revoked", revoked=True)

    resolver = ToolkitKeyResolver(control_db)
    assert await resolver.resolve(plaintext) is None


async def test_inactive_toolkit_resolves_to_none(
    control_db: DatabaseSession, clean_tables: None
) -> None:
    _tk_id, plaintext = await _seed_toolkit_key(
        control_db, toolkit_name="tk-inactive", active=False
    )

    resolver = ToolkitKeyResolver(control_db)
    assert await resolver.resolve(plaintext) is None
