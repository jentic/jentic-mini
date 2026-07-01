"""Integration tests for CatalogRepository (single-snapshot model)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import delete, select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.catalog_snapshots import SINGLETON_ID, CatalogSnapshot
from jentic_one.registry.repos.catalog_repo import CatalogRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration

_MANIFEST_URL = "https://example.com/apis.json"


def _entries() -> list[dict[str, Any]]:
    return [
        {
            "api_id": "stripe.com",
            "vendor": "stripe.com",
            "path": "apis/openapi/stripe.com/main",
            "spec_url": "https://example.com/stripe/openapi.json",
            "github_url": "https://github.com/jentic/jentic-public-apis/tree/main/x",
        },
        {
            "api_id": "slack.com",
            "vendor": "slack.com",
            "path": "apis/openapi/slack.com/main",
            "spec_url": "https://example.com/slack/openapi.json",
            "github_url": "https://github.com/jentic/jentic-public-apis/tree/main/y",
        },
    ]


@pytest.fixture()
async def clean_catalog(registry_db: DatabaseSession) -> None:
    async with registry_db.session() as session:
        await session.execute(delete(CatalogSnapshot))
        await session.commit()


async def test_replace_inserts_snapshot(registry_db: DatabaseSession, clean_catalog: None) -> None:
    async with registry_db.transaction() as session:
        n = await CatalogRepository.replace(session, source_url=_MANIFEST_URL, entries=_entries())
    assert n == 2

    async with registry_db.session() as session:
        snapshot = await CatalogRepository.current(session)
        entries = await CatalogRepository.entries(session)
    assert snapshot is not None
    assert snapshot.id == SINGLETON_ID
    assert snapshot.entry_count == 2
    assert snapshot.source_url == _MANIFEST_URL
    assert sorted(e["api_id"] for e in entries) == ["slack.com", "stripe.com"]


async def test_replace_swaps_previous_snapshot(
    registry_db: DatabaseSession, clean_catalog: None
) -> None:
    async with registry_db.transaction() as session:
        await CatalogRepository.replace(session, source_url=_MANIFEST_URL, entries=_entries())
    async with registry_db.transaction() as session:
        n = await CatalogRepository.replace(
            session, source_url=_MANIFEST_URL, entries=[{"api_id": "only.com"}]
        )
    assert n == 1
    async with registry_db.session() as session:
        entries = await CatalogRepository.entries(session)
        # exactly one current snapshot — the old one is gone, not accumulated
        all_snapshots = await session.execute(select(CatalogSnapshot))
        rows = list(all_snapshots.scalars().all())
    assert [e["api_id"] for e in entries] == ["only.com"]
    assert len(rows) == 1


async def test_fetched_at_none_when_empty(
    registry_db: DatabaseSession, clean_catalog: None
) -> None:
    async with registry_db.session() as session:
        assert await CatalogRepository.fetched_at(session) is None
        assert await CatalogRepository.entries(session) == []


async def test_fetched_at_set_after_replace(
    registry_db: DatabaseSession, clean_catalog: None
) -> None:
    async with registry_db.transaction() as session:
        await CatalogRepository.replace(session, source_url=_MANIFEST_URL, entries=_entries())
    async with registry_db.session() as session:
        ts = await CatalogRepository.fetched_at(session)
    assert ts is not None


async def test_registered_spec_urls_includes_unpromoted_draft_source(
    registry_db: DatabaseSession, clean_catalog: None, clean_registry: None
) -> None:
    """A draft revision's source_url counts as registered.

    Imports create a ``draft`` revision and never promote it to current, so
    coverage must count any non-archived revision — not just the current one —
    or freshly imported catalog entries would show ``registered=false`` forever.
    """
    spec_url = "https://example.com/stripe/openapi.json"
    api = Api(vendor="stripe", name="stripe-api", version="2024-01-01")
    async with registry_db.session() as session:
        session.add(api)
        await session.flush()
        # draft, and deliberately NOT set as current_revision_id (mirrors import)
        session.add(
            ApiRevision(
                api_id=api.id,
                state="draft",
                spec_digest="sha256:deadbeef",
                source_type="url",
                source_url=spec_url,
            )
        )
        await session.commit()

    async with registry_db.session() as session:
        urls = await CatalogRepository.registered_spec_urls(session)
    assert spec_url in urls


async def test_registered_spec_urls_excludes_archived(
    registry_db: DatabaseSession, clean_catalog: None, clean_registry: None
) -> None:
    """An archived revision's source_url must not keep masking a catalog entry."""
    spec_url = "https://example.com/archived/openapi.json"
    api = Api(vendor="old", name="old-api", version="v1")
    async with registry_db.session() as session:
        session.add(api)
        await session.flush()
        session.add(
            ApiRevision(
                api_id=api.id,
                state="archived",
                spec_digest="sha256:archived",
                source_type="url",
                source_url=spec_url,
            )
        )
        await session.commit()

    async with registry_db.session() as session:
        urls = await CatalogRepository.registered_spec_urls(session)
    assert spec_url not in urls
