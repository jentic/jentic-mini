"""Repository for ServiceAccountCredential CRUD."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.admin.core.schema.service_account_credentials import ServiceAccountCredential


class ServiceAccountCredentialRepository:
    """Data access layer for ServiceAccountCredential entities — flush-only, never commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        service_account_id: str,
        client_secret_hash: str | None = None,
        api_key_hash: str | None = None,
        created_by: str,
    ) -> ServiceAccountCredential:
        cred = ServiceAccountCredential(
            service_account_id=service_account_id,
            client_secret_hash=client_secret_hash,
            api_key_hash=api_key_hash,
            created_by=created_by,
        )
        session.add(cred)
        await session.flush()
        return cred

    @staticmethod
    async def get_by_service_account_id(
        session: AsyncSession, service_account_id: str
    ) -> ServiceAccountCredential | None:
        stmt = select(ServiceAccountCredential).where(
            ServiceAccountCredential.service_account_id == service_account_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def set_client_secret_hash(
        session: AsyncSession,
        service_account_id: str,
        *,
        client_secret_hash: str,
        created_by: str,
    ) -> ServiceAccountCredential:
        stmt = select(ServiceAccountCredential).where(
            ServiceAccountCredential.service_account_id == service_account_id
        )
        result = await session.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred is None:
            cred = ServiceAccountCredential(
                service_account_id=service_account_id,
                client_secret_hash=client_secret_hash,
                created_by=created_by,
            )
            session.add(cred)
        else:
            cred.client_secret_hash = client_secret_hash
            cred.rotated_at = datetime.now(UTC)
        await session.flush()
        return cred

    @staticmethod
    async def set_api_key_hash(
        session: AsyncSession,
        service_account_id: str,
        *,
        api_key_hash: str,
        created_by: str,
    ) -> ServiceAccountCredential:
        stmt = select(ServiceAccountCredential).where(
            ServiceAccountCredential.service_account_id == service_account_id
        )
        result = await session.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred is None:
            cred = ServiceAccountCredential(
                service_account_id=service_account_id,
                api_key_hash=api_key_hash,
                created_by=created_by,
            )
            session.add(cred)
        else:
            cred.api_key_hash = api_key_hash
            cred.rotated_at = datetime.now(UTC)
        await session.flush()
        return cred
