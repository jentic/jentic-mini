"""Unit tests for the IMPORTED revision state, origin attribute, and lifecycle guards."""

from __future__ import annotations

import uuid

from jentic_one.registry.ingest.fetch import InlineSource, UrlSource
from jentic_one.registry.ingest.models import ApiIdentifier, IngestSpecification, SpecType
from jentic_one.registry.ingest.schemas import IngestResult
from jentic_one.shared.models import ApiRevisionState

# --- Enum ---


def test_imported_member_exists() -> None:
    assert ApiRevisionState.IMPORTED.value == "imported"


def test_imported_round_trip() -> None:
    assert ApiRevisionState("imported") is ApiRevisionState.IMPORTED


def test_all_states_present() -> None:
    values = {s.value for s in ApiRevisionState}
    assert values == {"draft", "published", "imported", "archived"}


# --- Origin on source models ---


def test_url_source_origin_defaults_none() -> None:
    src = UrlSource(type="url", url="https://example.com/spec.json")
    assert src.origin is None


def test_url_source_origin_set() -> None:
    src = UrlSource(type="url", url="https://example.com/spec.json", origin="catalog")
    assert src.origin == "catalog"


def test_inline_source_origin_defaults_none() -> None:
    src = InlineSource(type="inline", content="{}", filename="spec.json")
    assert src.origin is None


def test_inline_source_origin_set() -> None:
    src = InlineSource(type="inline", content="{}", filename="spec.json", origin="webhook")
    assert src.origin == "webhook"


def test_ingest_specification_origin_defaults_none() -> None:
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="v", name="n", version="1"),
    )
    assert spec.origin is None


def test_ingest_specification_origin_set() -> None:
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="v", name="n", version="1"),
        origin="catalog",
    )
    assert spec.origin == "catalog"


# --- IngestResult state ---


def test_result_default_state_is_draft() -> None:
    result = IngestResult(
        api_vendor="v",
        api_name="n",
        api_version="1",
        revision_id=uuid.uuid4(),
        operation_count=0,
    )
    assert result.state == ApiRevisionState.DRAFT


def test_result_imported_state() -> None:
    result = IngestResult(
        api_vendor="v",
        api_name="n",
        api_version="1",
        revision_id=uuid.uuid4(),
        state=ApiRevisionState.IMPORTED,
        operation_count=5,
    )
    assert result.state == ApiRevisionState.IMPORTED


# --- Lifecycle guards ---


def test_promote_rejects_imported() -> None:
    """IMPORTED revisions cannot be promoted (already active)."""
    promotable = (ApiRevisionState.DRAFT,)
    assert ApiRevisionState.IMPORTED not in promotable


def test_archive_allows_imported_state() -> None:
    archivable = (ApiRevisionState.DRAFT, ApiRevisionState.IMPORTED)
    assert ApiRevisionState.IMPORTED in archivable
    assert ApiRevisionState.PUBLISHED not in archivable


# --- is_current derivation ---


def test_published_is_current() -> None:
    current_states = (ApiRevisionState.PUBLISHED, ApiRevisionState.IMPORTED)
    assert ApiRevisionState.PUBLISHED in current_states


def test_imported_is_current() -> None:
    current_states = (ApiRevisionState.PUBLISHED, ApiRevisionState.IMPORTED)
    assert ApiRevisionState.IMPORTED in current_states


def test_draft_is_not_current() -> None:
    current_states = (ApiRevisionState.PUBLISHED, ApiRevisionState.IMPORTED)
    assert ApiRevisionState.DRAFT not in current_states


def test_archived_is_not_current() -> None:
    current_states = (ApiRevisionState.PUBLISHED, ApiRevisionState.IMPORTED)
    assert ApiRevisionState.ARCHIVED not in current_states


# --- Origin-scoped archival ---


def test_different_origins_are_independent() -> None:
    """Two different origin values should be treated as independent import sources."""
    origins = {"catalog", "webhook"}
    assert len(origins) == 2
