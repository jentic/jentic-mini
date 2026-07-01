"""Repository for ServiceAccount CRUD."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from jentic_one.admin.core.schema.service_accounts import ServiceAccount
from jentic_one.admin.services.errors import ServiceAccountNotFoundError
from jentic_one.shared.models import ActorStatus


class ServiceAccountRepository:
    """Data access layer for ServiceAccount entities — flush-only, never commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        name: str,
        owner_id: str,
        registered_by: str,
        description: str | None = None,
        created_by: str,
    ) -> ServiceAccount:
        sa = ServiceAccount(
            name=name,
            owner_id=owner_id,
            registered_by=registered_by,
            description=description,
            created_by=created_by,
        )
        session.add(sa)
        await session.flush()
        return sa

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        service_account_id: str,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
    ) -> ServiceAccount | None:
        if filters is None:
            return await session.get(ServiceAccount, service_account_id)
        stmt = select(ServiceAccount).where(ServiceAccount.id == service_account_id)
        for f in filters:
            stmt = stmt.where(f)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_owner(
        session: AsyncSession,
        owner_id: str,
        *,
        limit: int = 50,
        cursor: datetime | None = None,
        filters: Sequence[ColumnElement[bool]] | None = None,
    ) -> list[ServiceAccount]:
        stmt = (
            select(ServiceAccount)
            .where(ServiceAccount.owner_id == owner_id)
            .order_by(ServiceAccount.created_at.desc())
            .limit(limit)
        )
        if cursor is not None:
            stmt = stmt.where(ServiceAccount.created_at < cursor)
        if filters is not None:
            for f in filters:
                stmt = stmt.where(f)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_all(
        session: AsyncSession,
        *,
        limit: int = 50,
        cursor: datetime | None = None,
        status: str | None = None,
        filters: Sequence[ColumnElement[bool]] | None = None,
    ) -> list[ServiceAccount]:
        stmt = select(ServiceAccount).order_by(ServiceAccount.created_at.desc()).limit(limit)
        if cursor is not None:
            stmt = stmt.where(ServiceAccount.created_at < cursor)
        if status is not None:
            stmt = stmt.where(ServiceAccount.status == status)
        if filters is not None:
            for f in filters:
                stmt = stmt.where(f)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        session: AsyncSession, service_account_id: str, status: ActorStatus
    ) -> ServiceAccount:
        svc_acct = await session.get(ServiceAccount, service_account_id)
        if svc_acct is None:
            raise ServiceAccountNotFoundError(service_account_id)
        svc_acct.status = status
        await session.flush()
        return svc_acct

    @staticmethod
    async def set_approval(
        session: AsyncSession, service_account_id: str, *, approved_by: str
    ) -> ServiceAccount:
        svc_acct = await session.get(ServiceAccount, service_account_id)
        if svc_acct is None:
            raise ServiceAccountNotFoundError(service_account_id)
        svc_acct.status = ActorStatus.ACTIVE
        svc_acct.approved_by = approved_by
        svc_acct.approved_at = datetime.now(UTC)
        await session.flush()
        return svc_acct

    @staticmethod
    async def set_denial(
        session: AsyncSession, service_account_id: str, *, reason: str, denied_by: str
    ) -> ServiceAccount:
        svc_acct = await session.get(ServiceAccount, service_account_id)
        if svc_acct is None:
            raise ServiceAccountNotFoundError(service_account_id)
        svc_acct.status = ActorStatus.REJECTED
        svc_acct.denial_reason = reason
        svc_acct.denied_by = denied_by
        await session.flush()
        return svc_acct

    @staticmethod
    async def get_by_id_for_update(
        session: AsyncSession, service_account_id: str
    ) -> ServiceAccount | None:
        stmt = (
            select(ServiceAccount).where(ServiceAccount.id == service_account_id).with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def archive(session: AsyncSession, service_account_id: str) -> ServiceAccount:
        svc_acct = await session.get(ServiceAccount, service_account_id)
        if svc_acct is None:
            raise ServiceAccountNotFoundError(service_account_id)
        svc_acct.status = ActorStatus.ARCHIVED
        await session.flush()
        return svc_acct
