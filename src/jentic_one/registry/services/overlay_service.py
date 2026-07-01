"""Overlay service — submission, retrieval, lifecycle transitions for overlays."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.repos.api_repo import ApiRepository
from jentic_one.registry.repos.overlay_repo import OverlayRepository
from jentic_one.registry.services.errors import (
    ApiNotFoundError,
    OverlayNotFoundError,
    OverlayStateConflictError,
)
from jentic_one.shared.audit import AuditAction, AuditTargetType, record_audit_best_effort
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.models import OverlayStatus
from jentic_one.shared.pagination import decode_cursor_str, encode_cursor


@dataclass(frozen=True)
class OverlayView:
    """Resolved view of a single overlay with context for link construction."""

    id: str
    api_id: uuid.UUID
    vendor: str
    name: str
    version: str
    status: str
    document: dict[str, Any]
    target_revision_id: uuid.UUID | None
    contributed_by: str | None
    confirmed_by_execution_id: str | None
    created_at: datetime
    updated_at: datetime | None
    confirmed_at: datetime | None
    deprecated_at: datetime | None


class OverlayPageItem(BaseModel):
    """View model for a single overlay in a paginated list."""

    id: str
    api_id: uuid.UUID
    status: str
    document: dict[str, Any]
    target_revision_id: uuid.UUID | None
    contributed_by: str | None
    confirmed_by_execution_id: str | None
    created_at: datetime
    updated_at: datetime | None
    confirmed_at: datetime | None
    deprecated_at: datetime | None


class OverlayPage(BaseModel):
    """Paginated result of overlays."""

    data: list[OverlayPageItem]
    has_more: bool
    next_cursor: str | None = None


class OverlayService:
    """Operations for overlay lifecycle management."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def _resolve_api(self, vendor: str, name: str, version: str) -> Api:
        async with self._ctx.registry_db.session() as session:
            api = await ApiRepository.get_by_identifier(session, vendor, name, version)
        if api is None:
            raise ApiNotFoundError(vendor, name, version)
        return api

    async def submit(
        self,
        vendor: str,
        name: str,
        version: str,
        document: dict[str, Any],
        target_revision_id: uuid.UUID | None = None,
        contributed_by: str | None = None,
        *,
        identity: Identity,
    ) -> OverlayView:
        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.transaction() as session:
            overlay = await OverlayRepository.create(
                session,
                api_id=api.id,
                document=document,
                target_revision_id=target_revision_id,
                contributed_by=contributed_by,
                created_by=identity.sub,
            )

        await record_audit_best_effort(
            self._ctx,
            action=AuditAction.CREATE,
            target_type=AuditTargetType.OVERLAY,
            target_id=overlay.id,
            actor_type=identity.actor_type,
            actor_id=identity.sub,
            target_parent_id=str(api.id),
            origin=identity.origin.value,
        )
        return OverlayView(
            id=overlay.id,
            api_id=overlay.api_id,
            vendor=vendor,
            name=name,
            version=version,
            status=overlay.status,
            document=overlay.document,
            target_revision_id=overlay.target_revision_id,
            contributed_by=overlay.contributed_by,
            confirmed_by_execution_id=overlay.confirmed_by_execution_id,
            created_at=overlay.created_at,
            updated_at=overlay.updated_at,
            confirmed_at=overlay.confirmed_at,
            deprecated_at=overlay.deprecated_at,
        )

    async def get(self, vendor: str, name: str, version: str, overlay_id: str) -> OverlayView:
        if not overlay_id.startswith("ovr_"):
            raise OverlayNotFoundError(overlay_id, vendor, name, version)

        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.session() as session:
            overlay = await OverlayRepository.get_for_api(session, api.id, overlay_id)

        if overlay is None:
            raise OverlayNotFoundError(overlay_id, vendor, name, version)

        return OverlayView(
            id=overlay.id,
            api_id=overlay.api_id,
            vendor=vendor,
            name=name,
            version=version,
            status=overlay.status,
            document=overlay.document,
            target_revision_id=overlay.target_revision_id,
            contributed_by=overlay.contributed_by,
            confirmed_by_execution_id=overlay.confirmed_by_execution_id,
            created_at=overlay.created_at,
            updated_at=overlay.updated_at,
            confirmed_at=overlay.confirmed_at,
            deprecated_at=overlay.deprecated_at,
        )

    async def list_page(
        self,
        vendor: str,
        name: str,
        version: str,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
    ) -> OverlayPage:
        cursor_created_at: datetime | None = None
        cursor_id: str | None = None
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor_str(cursor)

        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.session() as session:
            rows = await OverlayRepository.list_page(
                session,
                api_id=api.id,
                limit=limit + 1,
                cursor_created_at=cursor_created_at,
                cursor_id=cursor_id,
                status=status,
            )

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [
            OverlayPageItem(
                id=row.id,
                api_id=row.api_id,
                status=row.status,
                document=row.document,
                target_revision_id=row.target_revision_id,
                contributed_by=row.contributed_by,
                confirmed_by_execution_id=row.confirmed_by_execution_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                confirmed_at=row.confirmed_at,
                deprecated_at=row.deprecated_at,
            )
            for row in rows
        ]

        next_cursor: str | None = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return OverlayPage(data=items, has_more=has_more, next_cursor=next_cursor)

    async def update(
        self,
        vendor: str,
        name: str,
        version: str,
        overlay_id: str,
        document: dict[str, Any] | None = None,
        target_revision_id: uuid.UUID | None = None,
        *,
        identity: Identity,
    ) -> OverlayView:
        if not overlay_id.startswith("ovr_"):
            raise OverlayNotFoundError(overlay_id, vendor, name, version)

        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.transaction() as session:
            overlay = await OverlayRepository.get_for_api(session, api.id, overlay_id)
            if overlay is None:
                raise OverlayNotFoundError(overlay_id, vendor, name, version)

            if overlay.status != OverlayStatus.PENDING:
                raise OverlayStateConflictError(
                    overlay_id, overlay.status, [OverlayStatus.PENDING], "update"
                )

            await OverlayRepository.update_fields(
                session,
                overlay_id,
                document=document,
                target_revision_id=target_revision_id,
            )

            refreshed = await OverlayRepository.get_for_api(session, api.id, overlay_id)
            assert refreshed is not None

        await record_audit_best_effort(
            self._ctx,
            action=AuditAction.UPDATE,
            target_type=AuditTargetType.OVERLAY,
            target_id=overlay_id,
            actor_type=identity.actor_type,
            actor_id=identity.sub,
            target_parent_id=str(api.id),
            origin=identity.origin.value,
        )
        return OverlayView(
            id=refreshed.id,
            api_id=refreshed.api_id,
            vendor=vendor,
            name=name,
            version=version,
            status=refreshed.status,
            document=refreshed.document,
            target_revision_id=refreshed.target_revision_id,
            contributed_by=refreshed.contributed_by,
            confirmed_by_execution_id=refreshed.confirmed_by_execution_id,
            created_at=refreshed.created_at,
            updated_at=refreshed.updated_at,
            confirmed_at=refreshed.confirmed_at,
            deprecated_at=refreshed.deprecated_at,
        )

    async def confirm(
        self,
        vendor: str,
        name: str,
        version: str,
        overlay_id: str,
        execution_id: str | None = None,
        *,
        identity: Identity,
    ) -> OverlayView:
        if not overlay_id.startswith("ovr_"):
            raise OverlayNotFoundError(overlay_id, vendor, name, version)

        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.transaction() as session:
            overlay = await OverlayRepository.get_for_api(session, api.id, overlay_id)
            if overlay is None:
                raise OverlayNotFoundError(overlay_id, vendor, name, version)

            if overlay.status == OverlayStatus.CONFIRMED:
                return OverlayView(
                    id=overlay.id,
                    api_id=overlay.api_id,
                    vendor=vendor,
                    name=name,
                    version=version,
                    status=overlay.status,
                    document=overlay.document,
                    target_revision_id=overlay.target_revision_id,
                    contributed_by=overlay.contributed_by,
                    confirmed_by_execution_id=overlay.confirmed_by_execution_id,
                    created_at=overlay.created_at,
                    updated_at=overlay.updated_at,
                    confirmed_at=overlay.confirmed_at,
                    deprecated_at=overlay.deprecated_at,
                )

            if overlay.status != OverlayStatus.PENDING:
                raise OverlayStateConflictError(
                    overlay_id, overlay.status, [OverlayStatus.PENDING], "confirm"
                )

            now = datetime.now(UTC)
            await OverlayRepository.set_status(
                session,
                overlay_id,
                OverlayStatus.CONFIRMED,
                confirmed_at=now,
                confirmed_by_execution_id=execution_id,
            )

            refreshed = await OverlayRepository.get_for_api(session, api.id, overlay_id)
            assert refreshed is not None

        await record_audit_best_effort(
            self._ctx,
            action=AuditAction.CONFIRM,
            target_type=AuditTargetType.OVERLAY,
            target_id=overlay_id,
            actor_type=identity.actor_type,
            actor_id=identity.sub,
            target_parent_id=str(api.id),
            reason=f"confirmed by execution {execution_id}" if execution_id else None,
            origin=identity.origin.value,
        )
        return OverlayView(
            id=refreshed.id,
            api_id=refreshed.api_id,
            vendor=vendor,
            name=name,
            version=version,
            status=refreshed.status,
            document=refreshed.document,
            target_revision_id=refreshed.target_revision_id,
            contributed_by=refreshed.contributed_by,
            confirmed_by_execution_id=refreshed.confirmed_by_execution_id,
            created_at=refreshed.created_at,
            updated_at=refreshed.updated_at,
            confirmed_at=refreshed.confirmed_at,
            deprecated_at=refreshed.deprecated_at,
        )

    async def deprecate(
        self, vendor: str, name: str, version: str, overlay_id: str, *, identity: Identity
    ) -> None:
        if not overlay_id.startswith("ovr_"):
            raise OverlayNotFoundError(overlay_id, vendor, name, version)

        api = await self._resolve_api(vendor, name, version)

        async with self._ctx.registry_db.transaction() as session:
            overlay = await OverlayRepository.get_for_api(session, api.id, overlay_id)
            if overlay is None:
                raise OverlayNotFoundError(overlay_id, vendor, name, version)

            now = datetime.now(UTC)
            await OverlayRepository.set_status(
                session, overlay_id, OverlayStatus.DEPRECATED, deprecated_at=now
            )

        await record_audit_best_effort(
            self._ctx,
            action=AuditAction.DEPRECATE,
            target_type=AuditTargetType.OVERLAY,
            target_id=overlay_id,
            actor_type=identity.actor_type,
            actor_id=identity.sub,
            target_parent_id=str(api.id),
            origin=identity.origin.value,
        )
