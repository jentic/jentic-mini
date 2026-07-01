"""Integration tests verifying best-effort cross-DB audit for CredentialService.

The credential mutation commits against the control database, while the audit
entry is written best-effort against the admin database. These tests assert
that the expected audit rows are written and — critically — that secret values
never appear in the recorded before/after snapshots.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, select

from jentic_one.admin.core.schema.audit import AuditEntry
from jentic_one.control.core.schema.basic_credentials import BasicCredential
from jentic_one.control.core.schema.credentials import Credential
from jentic_one.control.core.schema.customer_api_keys import CustomerAPIKey
from jentic_one.control.core.schema.oauth_client_credentials import OAuthClientCredential
from jentic_one.control.core.schema.oauth_tokens import OAuthToken
from jentic_one.control.core.schema.token_value_credentials import TokenValueCredential
from jentic_one.control.services.credentials.schemas.credentials import (
    CredentialCreate,
    CredentialUpdate,
)
from jentic_one.control.services.credentials.schemas.provision import APIReference
from jentic_one.control.services.credentials.service import CredentialService
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models.audit import AuditAction, AuditTargetType
from jentic_one.shared.models.credentials import CredentialType

_ADMIN_IDENTITY = Identity(sub="admin_user", email="admin@test.com", permissions=["org:admin"])

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_credentials(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async def _wipe() -> None:
        async with control_db.session() as session:
            await session.execute(delete(OAuthToken))
            await session.execute(delete(TokenValueCredential))
            await session.execute(delete(BasicCredential))
            await session.execute(delete(OAuthClientCredential))
            await session.execute(delete(CustomerAPIKey))
            await session.execute(delete(Credential))
            await session.commit()

    await _wipe()
    yield
    await _wipe()


@pytest.fixture()
async def clean_audit(integration_context: Context) -> AsyncGenerator[None, None]:
    async def _wipe() -> None:
        async with integration_context.admin_db.session() as session:
            await session.execute(delete(AuditEntry))
            await session.commit()

    await _wipe()
    yield
    await _wipe()


@pytest.fixture()
def svc(integration_context: Context) -> CredentialService:
    return CredentialService(integration_context)


def _api() -> APIReference:
    return APIReference(vendor="test-vendor", name="test-api", version="v1")


async def _audit_entries_for(ctx: Context, target_id: str) -> list[AuditEntry]:
    async with ctx.admin_db.session() as session:
        result = await session.execute(
            select(AuditEntry)
            .where(
                AuditEntry.target_type == AuditTargetType.CREDENTIAL.value,
                AuditEntry.target_id == target_id,
            )
            .order_by(AuditEntry.occurred_at.desc())
        )
        return list(result.scalars().all())


async def test_create_records_audit_without_secret(
    integration_context: Context,
    svc: CredentialService,
    clean_credentials: None,
    clean_audit: None,
) -> None:
    secret = "sk-secret-token-value123"  # pragma: allowlist secret
    result = await svc.create(
        CredentialCreate(
            type=CredentialType.BEARER_TOKEN,
            name="My Token",
            api=_api(),
            token=secret,
        ),
        identity=_ADMIN_IDENTITY,
    )

    entries = await _audit_entries_for(integration_context, result.credential_id)
    create_entries = [e for e in entries if e.action == AuditAction.CREATE.value]
    assert len(create_entries) == 1
    entry = create_entries[0]
    assert entry.after is not None
    assert entry.after["name"] == "My Token"
    assert entry.after["type"] == str(CredentialType.BEARER_TOKEN)
    # The secret must never be recorded in the audit snapshot.
    assert secret not in str(entry.after)
    assert secret not in str(entry.before)
    assert secret not in str(entry.diff)


async def test_update_records_audit_without_secret(
    integration_context: Context,
    svc: CredentialService,
    clean_credentials: None,
    clean_audit: None,
) -> None:
    new_secret = "sk-rotated-secret-value999"  # pragma: allowlist secret
    created = await svc.create(
        CredentialCreate(
            type=CredentialType.BEARER_TOKEN,
            name="Original",
            api=_api(),
            token="sk-original-secret-value111",
        ),
        identity=_ADMIN_IDENTITY,
    )

    await svc.update(
        created.credential_id,
        CredentialUpdate(type=CredentialType.BEARER_TOKEN, name="Renamed", token=new_secret),
        identity=_ADMIN_IDENTITY,
    )

    entries = await _audit_entries_for(integration_context, created.credential_id)
    update_entries = [e for e in entries if e.action == AuditAction.UPDATE.value]
    assert len(update_entries) == 1
    entry = update_entries[0]
    assert new_secret not in str(entry.after)
    assert new_secret not in str(entry.before)
    assert new_secret not in str(entry.diff)


async def test_delete_records_audit(
    integration_context: Context,
    svc: CredentialService,
    clean_credentials: None,
    clean_audit: None,
) -> None:
    created = await svc.create(
        CredentialCreate(
            type=CredentialType.BEARER_TOKEN,
            name="To Delete",
            api=_api(),
            token="sk-delete-secret-value222",
        ),
        identity=_ADMIN_IDENTITY,
    )

    await svc.delete(created.credential_id, identity=_ADMIN_IDENTITY)

    entries = await _audit_entries_for(integration_context, created.credential_id)
    delete_entries = [e for e in entries if e.action == AuditAction.DELETE.value]
    assert len(delete_entries) == 1
    assert delete_entries[0].actor_id == _ADMIN_IDENTITY.sub
