"""Smoke tests: agent ingests the smoke-upstream harness, then discovers its ops.

Proves the front half of the broker round trip — login → ingest → list →
search → inspect — produces an indexed operation whose resolved ``url`` points
at the harness's in-cluster DNS, i.e. exactly the URL the agent later hands the
broker. The execute-through-broker half lives in the ``test_broker_execute_*``
modules.

All tests need the ingest + control surfaces, so they skip in ``MODE=broker``
(no admin/registry API) via ``_skip_if_no_admin_surface``; the autouse
reachability fixture skips when the app ``/health`` is down.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest

from tests.smoke.conftest import (
    HarnessApi,
    SmokeAgent,
    _skip_if_no_admin_surface,
    authed_request,
)


@pytest.mark.smoke
def test_agent_ingests_harness(harness_api: HarnessApi) -> None:
    """The harness live spec ingests and resolves to a concrete API identity."""
    _skip_if_no_admin_surface()
    assert harness_api.vendor
    assert harness_api.name
    assert harness_api.version
    # The live spec declares info.version 1.0.0; the registry derives the API
    # version from it.
    assert harness_api.version == "1.0.0"


@pytest.mark.smoke
def test_harness_listed(base_url: str, test_agent: SmokeAgent, harness_api: HarnessApi) -> None:
    """GET /apis?vendor=… includes the freshly ingested harness API."""
    _skip_if_no_admin_surface()
    body, status = authed_request(
        f"{base_url}/apis?vendor={harness_api.vendor}",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    matches = [
        a
        for a in body["data"]
        if a["api"]["vendor"] == harness_api.vendor and a["api"]["name"] == harness_api.name
    ]
    assert len(matches) >= 1


@pytest.mark.smoke
def test_harness_revisions(base_url: str, test_agent: SmokeAgent, harness_api: HarnessApi) -> None:
    """GET /apis/{v}/{n}/{ver}/revisions returns at least one revision."""
    _skip_if_no_admin_surface()
    body, status = authed_request(
        f"{base_url}/apis/{harness_api.vendor}/{harness_api.name}/{harness_api.version}/revisions",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert len(body["data"]) >= 1


@pytest.mark.smoke
def test_search_finds_harness_ops(
    base_url: str,
    test_agent: SmokeAgent,
    harness_api: HarnessApi,
    upstream_incluster_url: str,
) -> None:
    """Search surfaces a harness op whose resolved url points at the harness DNS.

    The query wording ("echo the request") matches the live-spec ``/behavior/echo``
    summary ("Echo the request"). The resolved ``url`` retains the ``:8084`` port
    (``_resolve_operation_url`` keeps the servers[].url base), proving the indexed
    URL is exactly what the agent hands the broker.
    """
    _skip_if_no_admin_surface()
    body, status = authed_request(
        f"{base_url}/search",
        method="POST",
        token=test_agent.access_token,
        body={"query": "echo the request"},
    )
    if status == 501:
        pytest.skip("Vector search not available in this deployment")
    assert status == 200
    assert isinstance(body, dict)

    # Filter to this test's API first so a sibling test's API on a shared cluster
    # can't satisfy the assertion.
    ours = [item for item in body["data"] if item["api"]["vendor"] == harness_api.vendor]
    assert ours, f"No search results for vendor {harness_api.vendor}: {body['data']}"
    assert any(item["url"].startswith(upstream_incluster_url) for item in ours), (
        f"No result url starts with {upstream_incluster_url}: {[i['url'] for i in ours]}"
    )


@pytest.mark.smoke
def test_inspect_operation_url(
    base_url: str,
    test_agent: SmokeAgent,
    harness_api: HarnessApi,
    upstream_incluster_url: str,
) -> None:
    """A discovered operation's url is the harness DNS with the :8084 port.

    Asserts the field shapes the broker relies on: ``url`` is the full URL *with*
    port; ``api.host`` is the hostname *without* the port (same port-stripping as
    ``servers/resolution``). Assert on ``url`` for the port, ``api.host`` otherwise.
    """
    _skip_if_no_admin_surface()
    body, status = authed_request(
        f"{base_url}/search",
        method="POST",
        token=test_agent.access_token,
        body={"query": "echo the request"},
    )
    if status == 501:
        pytest.skip("Vector search not available in this deployment")
    assert status == 200
    assert isinstance(body, dict)

    ours = [item for item in body["data"] if item["api"]["vendor"] == harness_api.vendor]
    assert ours, f"No search results for vendor {harness_api.vendor}"
    op = next(item for item in ours if item["url"].startswith(upstream_incluster_url))

    assert op["url"].startswith(f"{upstream_incluster_url}/")
    assert op["api"]["host"] == urlparse(upstream_incluster_url).hostname
