"""Repository for TokenValueCredential CRUD operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.control.core.schema.token_value_credentials import TokenValueCredential


class TokenValueCredentialRepository:
    """Data access layer for TokenValueCredential entities — flush-only, never commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        credential_id: str,
        encrypted_token_value: str,
        token_preview: str | None = None,
        expires_at: datetime | None = None,
        created_by: str,
    ) -> TokenValueCredential:
        row = TokenValueCredential(
            credential_id=credential_id,
            encrypted_token_value=encrypted_token_value,
            token_preview=token_preview,
            expires_at=expires_at,
            created_by=created_by,
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def get_by_credential(
        session: AsyncSession, credential_id: str
    ) -> TokenValueCredential | None:
        result = await session.execute(
            select(TokenValueCredential).where(TokenValueCredential.credential_id == credential_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_token(
        session: AsyncSession,
        credential_id: str,
        *,
        encrypted_token_value: str,
        token_preview: str | None = None,
    ) -> TokenValueCredential | None:
        row = await TokenValueCredentialRepository.get_by_credential(session, credential_id)
        if row is None:
            return None
        row.encrypted_token_value = encrypted_token_value
        row.token_preview = token_preview
        await session.flush()
        return row

    @staticmethod
    async def delete_by_credential(session: AsyncSession, credential_id: str) -> bool:
        row = await TokenValueCredentialRepository.get_by_credential(session, credential_id)
        if row is None:
            return False
        await session.delete(row)
        await session.flush()
        return True
