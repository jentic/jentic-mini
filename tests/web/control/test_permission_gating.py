"""Enforcement tests for least-privilege gating on control-plane read routes.

These lock in the route-guard behaviour introduced in the web-route permission
pass — both directions:

* An *under-scoped* caller (holds a real but unrelated scope) is **denied** 403
  on the newly gated reads, proving the gate is not a no-op.
* A *delegated agent* (minted ``owner:credentials:read`` / ``owner:toolkits:read``
  via ``DEFAULT_AGENT_SCOPES``, never the bare ``credentials:read`` /
  ``toolkits:read``) is **admitted** past the guard so the service-layer
  delegation filter (``control/scoping/filters.py``) can scope its owner's rows.
  Without the OR-listed owner scope on the guard the agent would be 403'd before
  that filter ever ran.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


# --- Under-scoped callers are denied (gate is real) ---


def test_list_credentials_denied_without_scope(wrong_scope_client: TestClient) -> None:
    assert wrong_scope_client.get("/credentials").status_code == 403


def test_get_credential_denied_without_scope(wrong_scope_client: TestClient) -> None:
    assert wrong_scope_client.get("/credentials/cred_anything").status_code == 403


def test_list_toolkits_denied_without_scope(wrong_scope_client: TestClient) -> None:
    assert wrong_scope_client.get("/toolkits").status_code == 403


def test_get_toolkit_denied_without_scope(wrong_scope_client: TestClient) -> None:
    assert wrong_scope_client.get("/toolkits/tk_anything").status_code == 403


# --- Delegated agents pass the guard (owner:* read is OR-listed) ---
#
# A non-403 status is the assertion: the request reaches the service layer (an
# empty list for /credentials and /toolkits, a 404 for a missing single resource)
# rather than being rejected at the guard. A 403 here would mean the delegation
# read path is broken over HTTP.


def test_delegated_agent_can_reach_list_credentials(delegated_agent_client: TestClient) -> None:
    resp = delegated_agent_client.get("/credentials")
    assert resp.status_code == 200, resp.text


def test_delegated_agent_can_reach_get_credential(delegated_agent_client: TestClient) -> None:
    # Owner-scoped + non-existent -> 404 from the service, never 403 from the guard.
    assert delegated_agent_client.get("/credentials/cred_missing").status_code == 404


def test_delegated_agent_can_reach_list_toolkits(delegated_agent_client: TestClient) -> None:
    resp = delegated_agent_client.get("/toolkits")
    assert resp.status_code == 200, resp.text


def test_delegated_agent_can_reach_get_toolkit(delegated_agent_client: TestClient) -> None:
    assert delegated_agent_client.get("/toolkits/tk_missing").status_code == 404
