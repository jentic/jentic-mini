"""Integration tests for the Credential ORM models against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, inspect, select

from jentic_one.control.core.schema.basic_credentials import BasicCredential
from jentic_one.control.core.schema.credentials import Credential
from jentic_one.control.core.schema.customer_api_keys import CustomerAPIKey
from jentic_one.control.core.schema.oauth_client_credentials import OAuthClientCredential
from jentic_one.control.core.schema.oauth_tokens import OAuthToken
from jentic_one.control.core.schema.token_value_credentials import TokenValueCredential
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import StoredCredentialType

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_credentials(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Ensure credential tables are empty before and after each test."""
    async with control_db.session() as session:
        await session.execute(delete(OAuthToken))
        await session.execute(delete(TokenValueCredential))
        await session.execute(delete(BasicCredential))
        await session.execute(delete(OAuthClientCredential))
        await session.execute(delete(CustomerAPIKey))
        await session.execute(delete(Credential))
        await session.commit()
    yield
    async with control_db.session() as session:
        await session.execute(delete(OAuthToken))
        await session.execute(delete(TokenValueCredential))
        await session.execute(delete(BasicCredential))
        await session.execute(delete(OAuthClientCredential))
        await session.execute(delete(CustomerAPIKey))
        await session.execute(delete(Credential))
        await session.commit()


async def test_credential_round_trip(control_db: DatabaseSession, clean_credentials: None) -> None:
    """A Credential can be inserted and read back with all fields intact."""
    cred = Credential(
        id="cred_test001",
        type=StoredCredentialType.API_KEY,
        name="Test API Key Credential",
        description="A test credential for integration testing",
        api_vendor="stripe",
        api_name="payments",
        api_version="v1",
    )

    async with control_db.session() as session:
        session.add(cred)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_test001"))
        loaded = result.scalar_one()

        assert loaded.id == "cred_test001"
        assert loaded.type == StoredCredentialType.API_KEY
        assert loaded.name == "Test API Key Credential"
        assert loaded.description == "A test credential for integration testing"
        assert loaded.api_vendor == "stripe"
        assert loaded.api_name == "payments"
        assert loaded.api_version == "v1"
        assert loaded.active is True
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        assert loaded.created_by is None


async def test_credential_with_customer_api_key_cascade(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """Deleting a Credential cascades to its CustomerAPIKey child."""
    cred = Credential(
        id="cred_cascade01",
        type=StoredCredentialType.API_KEY,
        name="Cascade Test",
        api_vendor="github",
    )
    api_key = CustomerAPIKey(
        id="key_test001",
        credential_id="cred_cascade01",
        encrypted_key="encrypted_abc123",
    )

    async with control_db.session() as session:
        session.add(cred)
        session.add(api_key)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(
            select(CustomerAPIKey).where(CustomerAPIKey.credential_id == "cred_cascade01")
        )
        assert result.scalar_one().encrypted_key == "encrypted_abc123"

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_cascade01"))
        loaded_cred = result.scalar_one()
        await session.delete(loaded_cred)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(
            select(CustomerAPIKey).where(CustomerAPIKey.credential_id == "cred_cascade01")
        )
        assert result.scalar_one_or_none() is None


async def test_credential_with_basic_credential_eager_load(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """BasicCredential is eagerly loaded via selectin on the Credential."""
    cred = Credential(
        id="cred_basic01",
        type=StoredCredentialType.BASIC_AUTH,
        name="Basic Auth Test",
        api_vendor="httpbin",
    )
    basic = BasicCredential(
        credential_id="cred_basic01",
        username="admin",
        encrypted_password="encrypted_secret",
    )

    async with control_db.session() as session:
        session.add(cred)
        session.add(basic)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_basic01"))
        loaded = result.scalar_one()
        assert loaded.basic_credential is not None
        assert loaded.basic_credential.username == "admin"
        assert loaded.basic_credential.encrypted_password == "encrypted_secret"


async def test_oauth_client_credential_shared_pk(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """OAuthClientCredential shares its PK with the parent Credential (strict 1:1)."""
    cred = Credential(
        id="cred_oauth01",
        type=StoredCredentialType.OAUTH2_CLIENT_CREDENTIALS,
        name="OAuth Client Creds",
        api_vendor="google",
    )
    oauth_creds = OAuthClientCredential(
        id="cred_oauth01",
        token_url="https://oauth2.googleapis.com/token",
        client_id="client-123",
        encrypted_client_secret="encrypted_secret456",
        scope="openid email",
    )

    async with control_db.session() as session:
        session.add(cred)
        session.add(oauth_creds)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(
            select(OAuthClientCredential).where(OAuthClientCredential.id == "cred_oauth01")
        )
        loaded = result.scalar_one()
        assert loaded.id == "cred_oauth01"
        assert loaded.token_url == "https://oauth2.googleapis.com/token"
        assert loaded.client_id == "client-123"
        assert loaded.scope == "openid email"


async def test_cascade_delete_removes_full_graph(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """Deleting a credential removes all sibling rows across all tables."""
    cred = Credential(
        id="cred_full01",
        type=StoredCredentialType.API_KEY,
        name="Full Graph Test",
        api_vendor="acme",
    )
    api_key = CustomerAPIKey(
        id="key_full01",
        credential_id="cred_full01",
        encrypted_key="encrypted_key_val",
    )
    basic = BasicCredential(
        credential_id="cred_full01",
        username="user",
        encrypted_password="encrypted_pass",
    )
    token_val = TokenValueCredential(
        credential_id="cred_full01",
        encrypted_token_value="encrypted_token",
    )
    oauth_token = OAuthToken(
        id="otok_full01",
        credential_id="cred_full01",
        encrypted_access_token="encrypted_access",
    )

    async with control_db.session() as session:
        session.add(cred)
        session.add(api_key)
        session.add(basic)
        session.add(token_val)
        session.add(oauth_token)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_full01"))
        loaded_cred = result.scalar_one()
        await session.delete(loaded_cred)
        await session.commit()

    async with control_db.session() as session:
        assert (
            await session.execute(
                select(CustomerAPIKey).where(CustomerAPIKey.credential_id == "cred_full01")
            )
        ).scalar_one_or_none() is None
        assert (
            await session.execute(
                select(BasicCredential).where(BasicCredential.credential_id == "cred_full01")
            )
        ).scalar_one_or_none() is None
        assert (
            await session.execute(
                select(TokenValueCredential).where(
                    TokenValueCredential.credential_id == "cred_full01"
                )
            )
        ).scalar_one_or_none() is None
        assert (
            await session.execute(
                select(OAuthToken).where(OAuthToken.credential_id == "cred_full01")
            )
        ).scalar_one_or_none() is None


async def test_credential_provider_defaults_to_static(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """A Credential without explicit provider defaults to 'static'."""
    cred = Credential(
        id="cred_prov01",
        type=StoredCredentialType.API_KEY,
        name="Provider Default Test",
        api_vendor="stripe",
    )

    async with control_db.session() as session:
        session.add(cred)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_prov01"))
        loaded = result.scalar_one()
        assert loaded.provider == "static"
        assert loaded.provider_account_ref is None


async def test_credential_provider_explicit_values(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """A Credential can be created with explicit provider and provider_account_ref."""
    cred = Credential(
        id="cred_prov02",
        type=StoredCredentialType.OAUTH2_CLIENT_CREDENTIALS,
        name="OAuth Provider Test",
        api_vendor="google",
        provider="direct_oauth2",
        provider_account_ref="acc_123",
    )

    async with control_db.session() as session:
        session.add(cred)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(select(Credential).where(Credential.id == "cred_prov02"))
        loaded = result.scalar_one()
        assert loaded.provider == "direct_oauth2"
        assert loaded.provider_account_ref == "acc_123"


async def test_credential_filter_by_provider(
    control_db: DatabaseSession, clean_credentials: None
) -> None:
    """Filtering by provider uses the ix_credentials_provider index."""
    creds = [
        Credential(
            id="cred_filt01",
            type=StoredCredentialType.API_KEY,
            name="Static One",
            api_vendor="stripe",
            provider="static",
        ),
        Credential(
            id="cred_filt02",
            type=StoredCredentialType.API_KEY,
            name="OAuth One",
            api_vendor="google",
            provider="direct_oauth2",
            provider_account_ref="acc_456",
        ),
    ]

    async with control_db.session() as session:
        session.add_all(creds)
        await session.commit()

    async with control_db.session() as session:
        result = await session.execute(
            select(Credential).where(Credential.provider == "direct_oauth2")
        )
        loaded = result.scalars().all()
        assert len(loaded) == 1
        assert loaded[0].id == "cred_filt02"
        assert loaded[0].provider_account_ref == "acc_456"


async def test_provider_index_exists(control_db: DatabaseSession) -> None:
    """The ix_credentials_provider index exists on the credentials table."""
    async with control_db.session() as session:
        conn = await session.connection()
        indexes = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("credentials")
        )
        index_names = [idx["name"] for idx in indexes]
        assert "ix_credentials_provider" in index_names
