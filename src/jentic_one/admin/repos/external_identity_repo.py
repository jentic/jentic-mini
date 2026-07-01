"""Repository for ExternalIdentity CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.admin.core.schema.external_identities import ExternalIdentity


class ExternalIdentityRepository:
    """Data access layer for ExternalIdentity entities — flush-only, never commits."""

    @staticmethod
    async def get_by_provider_subject(
        session: AsyncSession, provider: str, external_subject: str
    ) -> ExternalIdentity | None:
        stmt = select(ExternalIdentity).where(
            ExternalIdentity.provider == provider,
            ExternalIdentity.external_subject == external_subject,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        provider: str,
        external_subject: str,
        user_id: str,
        email: str | None = None,
        created_by: str,
    ) -> ExternalIdentity:
        ext_id = ExternalIdentity(
            provider=provider,
            external_subject=external_subject,
            user_id=user_id,
            email=email,
            created_by=created_by,
        )
        session.add(ext_id)
        await session.flush()
        return ext_id
