"""Repository for BasicCredential CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.control.core.schema.basic_credentials import BasicCredential


class BasicCredentialRepository:
    """Data access layer for BasicCredential entities — flush-only, never commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        credential_id: str,
        username: str,
        encrypted_password: str,
        created_by: str,
    ) -> BasicCredential:
        row = BasicCredential(
            credential_id=credential_id,
            username=username,
            encrypted_password=encrypted_password,
            created_by=created_by,
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def get_by_credential(
        session: AsyncSession, credential_id: str
    ) -> BasicCredential | None:
        result = await session.execute(
            select(BasicCredential).where(BasicCredential.credential_id == credential_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        session: AsyncSession,
        credential_id: str,
        *,
        username: str | None = None,
        encrypted_password: str | None = None,
    ) -> BasicCredential | None:
        row = await BasicCredentialRepository.get_by_credential(session, credential_id)
        if row is None:
            return None
        if username is not None:
            row.username = username
        if encrypted_password is not None:
            row.encrypted_password = encrypted_password
        await session.flush()
        return row

    @staticmethod
    async def delete_by_credential(session: AsyncSession, credential_id: str) -> bool:
        row = await BasicCredentialRepository.get_by_credential(session, credential_id)
        if row is None:
            return False
        await session.delete(row)
        await session.flush()
        return True
