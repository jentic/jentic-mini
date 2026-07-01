"""HTTP fetch helper for the catalog slice — SSRF-guarded GET of JSON documents.

A thin, redirect-safe wrapper around ``httpx.AsyncClient`` that reuses the same
``validate_upstream_url`` SSRF guard and ingest-config knobs (timeout, size cap,
redirect budget) as the import fetch layer. It exists so the catalog service can
pull the upstream manifest + individual specs without duplicating the redirect/size
hardening and without coupling to the ingest pipeline's spec-shaped return type.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from jentic_one.shared.config import IngestConfig
from jentic_one.shared.url_validation import validate_upstream_url


class CatalogFetchError(Exception):
    """Raised when an upstream catalog document cannot be fetched or parsed."""


async def fetch_json(url: str, *, config: IngestConfig) -> dict[str, Any]:
    """GET a URL and parse the body as JSON, with SSRF + redirect + size guards.

    Mirrors the hardening in ``registry.ingest.fetch.load_specification`` (manual
    redirect following with per-hop URL revalidation, content-length + body-size
    caps) but returns a plain decoded JSON object instead of an IngestSpecification.
    """
    try:
        validated_url = validate_upstream_url(url)
    except ValueError as exc:
        raise CatalogFetchError(f"unsafe URL rejected: {exc}") from exc

    max_bytes = config.max_spec_bytes
    try:
        async with httpx.AsyncClient(
            timeout=config.fetch_timeout_s, follow_redirects=False
        ) as client:
            resp = await client.get(validated_url)
            for _ in range(config.max_redirects):
                if resp.status_code < 300 or resp.status_code >= 400:
                    break
                location = resp.headers.get("location")
                if not location:
                    break
                try:
                    validated_url = validate_upstream_url(urljoin(validated_url, location))
                except ValueError as exc:
                    raise CatalogFetchError(f"unsafe URL rejected: {exc}") from exc
                resp = await client.get(validated_url)
            else:
                if 300 <= resp.status_code < 400:
                    raise CatalogFetchError("too many redirects")
    except CatalogFetchError:
        raise
    except httpx.HTTPError as exc:
        raise CatalogFetchError(f"failed to fetch {url}: {exc}") from exc

    if resp.status_code < 200 or resp.status_code >= 300:
        raise CatalogFetchError(f"non-success status {resp.status_code} fetching {url}")

    content_length = resp.headers.get("content-length")
    limit_mb = max_bytes / (1024 * 1024)
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        raise CatalogFetchError(f"response exceeds size limit ({limit_mb:.0f} MB)")
    if len(resp.content) > max_bytes:
        raise CatalogFetchError(f"response exceeds size limit ({limit_mb:.0f} MB)")

    try:
        parsed = json.loads(resp.text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise CatalogFetchError(f"failed to parse JSON from {url}") from exc

    if not isinstance(parsed, dict):
        raise CatalogFetchError("expected a JSON object")
    return parsed
