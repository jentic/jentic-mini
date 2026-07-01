"""Unit tests for ingest domain models."""

from typing import Any

import pytest
from pydantic import ValidationError

from jentic_one.registry.ingest.models import ApiIdentifier, IngestSpecification, SpecType
from jentic_one.shared.models import ApiRevisionSourceType


def test_spec_type_openapi_value() -> None:
    assert SpecType.OPENAPI.value == "openapi"


def test_spec_type_round_trip() -> None:
    assert SpecType("openapi") is SpecType.OPENAPI


def test_spec_type_invalid_value_raises() -> None:
    with pytest.raises(ValueError):
        SpecType("invalid")


def test_api_identifier_str_representation() -> None:
    ident = ApiIdentifier(vendor="acme", name="widgets", version="v1")
    assert str(ident) == "acme/widgets/v1"


def test_api_identifier_api_name_property() -> None:
    ident = ApiIdentifier(vendor="acme", name="widgets", version="v1")
    assert ident.api_name == "acme/widgets"


def test_api_identifier_default_filename() -> None:
    ident = ApiIdentifier(vendor="acme", name="widgets", version="v1")
    assert ident.filename == "openapi.json"


def test_api_identifier_custom_filename() -> None:
    ident = ApiIdentifier(vendor="acme", name="widgets", version="v1", filename="spec.yaml")
    assert ident.filename == "spec.yaml"


def test_ingest_specification_to_log_string_excludes_content() -> None:
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="acme", name="api", version="v1"),
        sha="abc123",
        content={"openapi": "3.1.0", "paths": {}},
    )
    log_str = spec.to_log_string()
    assert "content" not in log_str
    assert "openapi" in log_str
    assert "abc123" in log_str


def test_ingest_specification_invalid_spec_type_raises() -> None:
    with pytest.raises(ValidationError):
        IngestSpecification(
            spec_type="invalid",  # type: ignore[arg-type]
            api_identifier=ApiIdentifier(vendor="a", name="b", version="v1"),
        )


def test_ingest_specification_optional_fields_default_none() -> None:
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="a", name="b", version="v1"),
    )
    assert spec.sha is None
    assert spec.metadata is None
    assert spec.content is None
    assert spec.source_id is None
    assert spec.source_type is None
    assert spec.source_url is None
    assert spec.source_filename is None
    assert spec.submitted_by is None


def test_ingest_specification_source_tracking_fields() -> None:
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="a", name="b", version="v1"),
        source_id="src-1",
        source_type=ApiRevisionSourceType.URL,
        source_url="https://example.com/spec.json",
        source_filename="spec.json",
        submitted_by="user@example.com",
    )
    assert spec.source_id == "src-1"
    assert spec.source_type == ApiRevisionSourceType.URL
    assert spec.source_url == "https://example.com/spec.json"
    assert spec.source_filename == "spec.json"
    assert spec.submitted_by == "user@example.com"


def test_ingest_specification_to_log_string_with_metadata() -> None:
    metadata: dict[str, Any] = {"key": "value"}
    spec = IngestSpecification(
        spec_type=SpecType.OPENAPI,
        api_identifier=ApiIdentifier(vendor="a", name="b", version="v1"),
        metadata=metadata,
    )
    log_str = spec.to_log_string()
    assert "metadata" in log_str
