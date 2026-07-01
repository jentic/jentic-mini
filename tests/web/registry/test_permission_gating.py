"""Enforcement tests for least-privilege gating on registry read routes.

Two complementary directions:

* An under-scoped caller (holds an unrelated scope) is **denied** 403 on
  ``GET /apis``, proving the gate is real and not a no-op.
* A caller holding only ``apis:write`` is **admitted** to ``GET /apis`` — the
  route guard expands implications (``apis:write`` ⇒ ``apis:read``) so the
  advertised catalogue semantics hold at enforcement, not just in the docs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


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
