"""Tests for the catalog slice's SSRF-guarded JSON fetch helper (``fetch_json``).

Focuses on the response size guard, which gates catalog manifest + spec
previews. A regression here (the cap being too small) made large public-API
specs un-previewable with ``catalog spec unavailable: response exceeds size
limit``; these tests pin the configured limit and the labelled error message.
"""

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from jentic_one.registry.services.catalog.fetch import CatalogFetchError, fetch_json
from jentic_one.shared.config import IngestConfig

_SPEC: dict[str, Any] = {"openapi": "3.1.0", "info": {"title": "Big API", "version": "1.0.0"}}
_SPEC_BYTES = json.dumps(_SPEC).encode()


def _mock_client(
    body: bytes = _SPEC_BYTES,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.AsyncClient:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            content=body,
            headers=headers or {"content-type": "application/json"},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _patched(client: httpx.AsyncClient) -> Any:
    return patch(
        "jentic_one.registry.services.catalog.fetch.httpx.AsyncClient",
        return_value=client,
    )


@pytest.mark.asyncio
async def test_default_cap_is_25_mib() -> None:
    """A 20 MiB spec (was over the old 5 MiB cap) now fetches successfully."""
    big = b'{"openapi":"3.1.0","info":{"title":"x","version":"1"},"_pad":"'
    big += b"a" * (20 * 1024 * 1024) + b'"}'
    client = _mock_client(body=big)
    with _patched(client):
        result = await fetch_json("https://example.com/openapi.json", config=IngestConfig())
    assert result["openapi"] == "3.1.0"


@pytest.mark.asyncio
async def test_oversized_body_raises_with_limit_label() -> None:
    big_body = b"x" * (26 * 1024 * 1024)
    client = _mock_client(body=big_body)
    with _patched(client), pytest.raises(CatalogFetchError, match=r"size limit \(25 MB\)"):
        await fetch_json("https://example.com/openapi.json", config=IngestConfig())


@pytest.mark.asyncio
async def test_oversized_content_length_raises_with_limit_label() -> None:
    client = _mock_client(
        body=b"small",
        headers={"content-length": "40000000", "content-type": "application/json"},
    )
    with _patched(client), pytest.raises(CatalogFetchError, match=r"size limit \(25 MB\)"):
        await fetch_json("https://example.com/openapi.json", config=IngestConfig())


@pytest.mark.asyncio
async def test_custom_cap_is_respected() -> None:
    """The cap tracks IngestConfig.max_spec_bytes, so a tuned-down deploy still guards."""
    client = _mock_client(body=b"x" * 2048)
    with _patched(client), pytest.raises(CatalogFetchError, match="size limit"):
        await fetch_json(
            "https://example.com/openapi.json",
            config=IngestConfig(max_spec_bytes=1024),
        )
