"""Repository for connect-state nonce consumption (single-use enforcement)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CursorResult
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.control.core.schema.connect_nonces import ConnectNonce


class ConnectNonceRepository:
    """Data access layer for connect nonce consumption — flush-only, never commits."""

    @staticmethod
    async def consume(
        session: AsyncSession,
        *,
        nonce: str,
        credential_id: str,
        expires_at: datetime,
        created_by: str,
    ) -> bool:
        """Consume a nonce. Returns True if consumed, False if already used/expired."""
        if expires_at <= datetime.now(UTC):
            return False

        stmt = (
            pg_insert(ConnectNonce)
            .values(
                nonce=nonce,
                credential_id=credential_id,
                expires_at=expires_at,
                created_by=created_by,
            )
            .on_conflict_do_nothing(index_elements=["nonce"])
        )
        cursor_result: CursorResult[tuple[()]] = await session.execute(stmt)  # type: ignore[assignment]
        return bool(cursor_result.rowcount)
