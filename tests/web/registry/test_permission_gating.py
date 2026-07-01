"""Enforcement tests for least-privilege gating on registry read routes.

Two complementary directions:

* An under-scoped caller (holds an unrelated scope) is **denied** 403 on
  ``GET /apis``, proving the gate is real and not a no-op.
* A caller holding only ``apis:write`` is **admitted** to ``GET /apis`` — the
  route guard expands implications (``apis:write`` ⇒ ``apis:read``) so the
  advertised catalogue semantics hold at enforcement, not just in the docs.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterator
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from jentic_one.registry.core.schema.catalog_snapshots import CatalogSnapshot
from jentic_one.shared.context import Context

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _empty_catalog_manifest() -> Iterator[None]:
    """Pin the upstream catalog fetch to an empty manifest (no network, no ``stripe.com``).

    These gating tests assert that ``POST /catalog/{api_id}:import`` reaches the
    catalog resolver and returns 404 for a non-existent entry (proving it passed
    the 403 authorization guard). Without this, the lazy refresh-on-read hits the
    live public manifest, which now contains ``stripe.com`` — the import then
    succeeds (202) and the gate assertion breaks. Serving an empty manifest keeps
    the test hermetic and guarantees the entry is always absent.
    """
    real_client_cls = httpx.AsyncClient

    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps({"include": []}).encode(),
            headers={"content-type": "application/json"},
        )

    def _factory(*_args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return real_client_cls(transport=httpx.MockTransport(_handler), **kwargs)  # type: ignore[arg-type]

    with patch("jentic_one.registry.services.catalog.fetch.httpx.AsyncClient", _factory):
        yield


@pytest.fixture(autouse=True)
async def _clean_catalog(web_context: Context) -> AsyncGenerator[None, None]:
    """Empty the catalog snapshot around each test.

    A snapshot left by another test (populated from the live manifest, which now
    carries ``stripe.com``) is not stale, so the lazy refresh-on-read never fires
    and the empty-manifest mock above is bypassed — leaving ``stripe.com``
    resolvable and the import returning 202. Truncating forces the resolver to
    (re)fetch through the mock, guaranteeing the entry is absent (404).
    """

    async def _truncate() -> None:
        async with web_context.registry_db.session() as session:
            await session.execute(delete(CatalogSnapshot))
            await session.commit()

    await _truncate()
    yield
    await _truncate()


def test_list_apis_denied_without_scope(wrong_scope_client: TestClient) -> None:
    assert wrong_scope_client.get("/apis").status_code == 403


def test_write_scope_implies_read_on_list_apis(write_only_client: TestClient) -> None:
    # apis:write implies apis:read — the guard must expand it, so this is 200 not 403.
    assert write_only_client.get("/apis").status_code == 200


def test_catalog_import_scope_implies_read_on_list_apis(catalog_import_client: TestClient) -> None:
    # catalog:import implies apis:read.
    assert catalog_import_client.get("/apis").status_code == 200


def test_catalog_import_endpoint_gating(
    catalog_import_client: TestClient, write_only_client: TestClient, wrong_scope_client: TestClient
) -> None:
    """Verify POST /catalog/{api_id}:import is allowed for catalog:import and apis:write."""
    # 404 means it passed the 403 authorization guard and tried to resolve the catalog entry.
    assert catalog_import_client.post("/catalog/stripe.com:import").status_code == 404

    # apis:write implies catalog:import, so it also passes authorization.
    assert write_only_client.post("/catalog/stripe.com:import").status_code == 404

    # Unrelated scope is denied.
    assert wrong_scope_client.post("/catalog/stripe.com:import").status_code == 403


def test_apis_import_endpoint_gating(catalog_import_client: TestClient) -> None:
    """Verify POST /apis (URL/inline import) requires apis:write and denies catalog:import."""
    payload = {"source": {"url": "https://example.com/openapi.yaml"}}
    assert catalog_import_client.post("/apis", json=payload).status_code == 403
