"""Unit tests for consolidated APIReference models."""

import pytest
from pydantic import ValidationError

from jentic_one.control.services.credentials.schemas.provision import ServiceAPIReference
from jentic_one.shared.schemas import APIReference, APIReferenceRequest
from jentic_one.shared.schemas import APIReference as APIReferenceResponse


def test_api_reference_valid_construction() -> None:
    ref = APIReference(vendor="acme", name="payments", version="v1")
    assert ref.vendor == "acme"
    assert ref.name == "payments"
    assert ref.version == "v1"


def test_api_reference_missing_vendor_raises() -> None:
    with pytest.raises(ValidationError):
        APIReference(name="payments", version="v1")  # type: ignore[call-arg]


def test_api_reference_missing_name_raises() -> None:
    with pytest.raises(ValidationError):
        APIReference(vendor="acme", version="v1")  # type: ignore[call-arg]


def test_api_reference_missing_version_raises() -> None:
    with pytest.raises(ValidationError):
        APIReference(vendor="acme", name="payments")  # type: ignore[call-arg]


def test_request_defaults_for_name_and_version() -> None:
    ref = APIReferenceRequest(vendor="acme")
    assert ref.vendor == "acme"
    assert ref.name == ""
    assert ref.version == ""


def test_request_explicit_values() -> None:
    ref = APIReferenceRequest(vendor="acme", name="payments", version="v2")
    assert ref.name == "payments"
    assert ref.version == "v2"


def test_request_missing_vendor_raises() -> None:
    with pytest.raises(ValidationError):
        APIReferenceRequest()  # type: ignore[call-arg]


def test_service_api_reference_inherits_base_fields() -> None:
    ref = ServiceAPIReference(vendor="acme", name="payments", version="v1")
    assert ref.vendor == "acme"
    assert ref.name == "payments"
    assert ref.version == "v1"
    assert ref.host is None


def test_service_api_reference_optional_host() -> None:
    ref = ServiceAPIReference(
        vendor="acme", name="payments", version="v1", host="https://api.acme.com"
    )
    assert ref.host == "https://api.acme.com"


def test_service_api_reference_is_subclass_of_base() -> None:
    ref = ServiceAPIReference(vendor="acme", name="payments", version="v1")
    assert isinstance(ref, APIReference)


def test_response_alias_identity() -> None:
    assert APIReferenceResponse is APIReference


def test_response_serialization_identical() -> None:
    base = APIReference(vendor="acme", name="payments", version="v1")
    resp = APIReferenceResponse(vendor="acme", name="payments", version="v1")
    assert base.model_dump() == resp.model_dump()
