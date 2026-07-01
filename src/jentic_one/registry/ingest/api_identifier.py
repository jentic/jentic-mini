"""API identifier resolution — extracts ApiIdentifier from spec content and overrides."""

import re
from typing import Any

from jentic_one.registry.ingest.exc import IngestStageError
from jentic_one.registry.ingest.models import ApiIdentifier

_MAX_FIELD_LENGTH = 100
_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slugify(value: str) -> str:
    """Lowercase, strip, replace non-alphanumeric with hyphens, truncate."""
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug[:_MAX_FIELD_LENGTH]


def resolve_api_identifier(
    content: dict[str, Any],
    *,
    vendor: str | None = None,
    name: str | None = None,
    version: str | None = None,
) -> ApiIdentifier:
    """Resolve an ApiIdentifier from spec content with optional overrides.

    Precedence: explicit kwargs > info block fields.
    """
    info: dict[str, Any] = content.get("info", {}) if isinstance(content.get("info"), dict) else {}

    resolved_vendor = vendor or info.get("x-vendor") or (info.get("contact", {}) or {}).get("name")
    resolved_name = name or info.get("title")
    resolved_version = version or info.get("version")

    missing: list[str] = []
    if not resolved_vendor:
        missing.append("vendor")
    if not resolved_name:
        missing.append("name")
    if not resolved_version:
        missing.append("version")

    if missing:
        raise IngestStageError(f"cannot resolve api_identifier: missing {', '.join(missing)}")

    assert resolved_vendor is not None
    assert resolved_name is not None
    assert resolved_version is not None

    return ApiIdentifier(
        vendor=_slugify(resolved_vendor),
        name=_slugify(resolved_name),
        version=str(resolved_version).strip(),
    )
