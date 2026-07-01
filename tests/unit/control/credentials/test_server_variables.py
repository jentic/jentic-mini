"""Unit tests for server_variables in credential schemas (pure logic, no DB)."""

from datetime import UTC, datetime

from jentic_one.control.services.credentials.schemas.credentials import (
    BearerTokenRedacted,
    CredentialCreate,
    CredentialRedactedView,
    CredentialUpdate,
)
from jentic_one.control.services.credentials.schemas.provision import APIReference
from jentic_one.shared.models.credentials import CredentialType


def test_create_accepts_server_variables() -> None:
    payload = CredentialCreate(
        type=CredentialType.BEARER_TOKEN,
        name="Test",
        api=APIReference(vendor="acme.com", name="acme", version="v1"),
        server_variables={"your-domain": "acme", "region": "us"},
        token="secret",
    )
    assert payload.server_variables == {"your-domain": "acme", "region": "us"}


def test_create_server_variables_defaults_to_none() -> None:
    payload = CredentialCreate(
        type=CredentialType.BEARER_TOKEN,
        name="Test",
        api=APIReference(vendor="acme.com", name="acme", version="v1"),
        token="secret",
    )
    assert payload.server_variables is None


def test_create_server_variables_accepts_empty_dict() -> None:
    payload = CredentialCreate(
        type=CredentialType.BEARER_TOKEN,
        name="Test",
        api=APIReference(vendor="acme.com", name="acme", version="v1"),
        server_variables={},
        token="secret",
    )
    assert payload.server_variables == {}


def test_update_accepts_server_variables() -> None:
    payload = CredentialUpdate(
        type=CredentialType.BEARER_TOKEN,
        server_variables={"domain": "new-value"},
    )
    assert payload.server_variables == {"domain": "new-value"}


def test_update_server_variables_defaults_to_none() -> None:
    payload = CredentialUpdate(type=CredentialType.BEARER_TOKEN)
    assert payload.server_variables is None


def test_redacted_view_serializes_server_variables() -> None:
    view = CredentialRedactedView(
        credential_id="cred_123",
        type=CredentialType.BEARER_TOKEN,
        name="Test",
        api=APIReference(vendor="acme.com", name="acme", version="v1"),
        provider="static",
        active=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        details=BearerTokenRedacted(token_preview="…abc"),
        server_variables={"region": "us", "domain": "acme"},
    )
    data = view.model_dump()
    assert data["server_variables"] == {"region": "us", "domain": "acme"}


def test_redacted_view_none_server_variables() -> None:
    view = CredentialRedactedView(
        credential_id="cred_123",
        type=CredentialType.BEARER_TOKEN,
        name="Test",
        api=APIReference(vendor="acme.com", name="acme", version="v1"),
        provider="static",
        active=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        details=BearerTokenRedacted(token_preview="…abc"),
    )
    assert view.server_variables is None
