"""Repository for CustomerAPIKey CRUD operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.control.core.schema.customer_api_keys import CustomerAPIKey


class CustomerAPIKeyRepository:
    """Data access layer for CustomerAPIKey entities — flush-only, never commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        credential_id: str,
        encrypted_key: str,
        key_preview: str | None = None,
        expires_at: datetime | None = None,
        location: str = "header",
        field_name: str = "Authorization",
        created_by: str,
    ) -> CustomerAPIKey:
        row = CustomerAPIKey(
            credential_id=credential_id,
            encrypted_key=encrypted_key,
            key_preview=key_preview,
            expires_at=expires_at,
            location=location,
            field_name=field_name,
            created_by=created_by,
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def get_by_credential(session: AsyncSession, credential_id: str) -> CustomerAPIKey | None:
        result = await session.execute(
            select(CustomerAPIKey).where(CustomerAPIKey.credential_id == credential_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_key(
        session: AsyncSession,
        credential_id: str,
        *,
        encrypted_key: str,
        key_preview: str | None = None,
    ) -> CustomerAPIKey | None:
        row = await CustomerAPIKeyRepository.get_by_credential(session, credential_id)
        if row is None:
            return None
        row.encrypted_key = encrypted_key
        row.key_preview = key_preview
        await session.flush()
        return row

    @staticmethod
    async def delete_by_credential(session: AsyncSession, credential_id: str) -> bool:
        row = await CustomerAPIKeyRepository.get_by_credential(session, credential_id)
        if row is None:
            return False
        await session.delete(row)
        await session.flush()
        return True
