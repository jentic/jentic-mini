"""Repository for ProviderConfigRecord CRUD — flush-only, never commits."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.admin.core.schema.provider_configs import ProviderConfigRecord


class ProviderConfigRepository:
    """Data access layer for ProviderConfigRecord entities."""

    @staticmethod
    async def upsert(
        session: AsyncSession,
        *,
        name: str,
        config_json: dict[str, Any],
        created_by: str | None,
    ) -> ProviderConfigRecord:
        """Insert or update a provider config keyed by its unique name."""
        record = await ProviderConfigRepository.get(session, name)
        if record is None:
            record = ProviderConfigRecord(
                name=name,
                config_json=config_json,
                created_by=created_by,
            )
            session.add(record)
        else:
            record.config_json = config_json
        await session.flush()
        return record

    @staticmethod
    async def get(session: AsyncSession, name: str) -> ProviderConfigRecord | None:
        stmt = select(ProviderConfigRecord).where(ProviderConfigRecord.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(session: AsyncSession) -> list[ProviderConfigRecord]:
        stmt = select(ProviderConfigRecord).order_by(ProviderConfigRecord.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())
