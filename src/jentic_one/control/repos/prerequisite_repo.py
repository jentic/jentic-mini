"""Cross-database prerequisite queries for access request validation.

Uses raw SQL (text()) to avoid importing admin ORM models — the control module
must not import from the admin module.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BoundAgentRow(NamedTuple):
    """Result row for agents bound to a toolkit."""

    binding_id: str
    agent_id: str
    agent_name: str
    agent_status: str
    agent_created_at: datetime
    bound_at: datetime


class PrerequisiteRepository:
    """Checks existence of bindings in the admin database without admin imports."""

    @staticmethod
    async def agent_toolkit_binding_exists(
        session: AsyncSession, *, agent_id: str, toolkit_id: str
    ) -> bool:
        """Return True if a binding exists between the given agent and toolkit."""
        result = await session.execute(
            text(
                "SELECT 1 FROM agent_toolkit_bindings "
                "WHERE agent_id = :agent_id AND toolkit_id = :toolkit_id LIMIT 1"
            ),
            {"agent_id": agent_id, "toolkit_id": toolkit_id},
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def delete_agent_toolkit_bindings_for_toolkit(
        session: AsyncSession, *, toolkit_id: str
    ) -> int:
        """Delete all agent-toolkit bindings for a toolkit (cross-DB cleanup)."""
        result = await session.execute(
            text("DELETE FROM agent_toolkit_bindings WHERE toolkit_id = :toolkit_id"),
            {"toolkit_id": toolkit_id},
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    @staticmethod
    async def list_agents_for_toolkit(
        session: AsyncSession,
        *,
        toolkit_id: str,
        cursor: tuple[datetime, str] | None = None,
        limit: int = 50,
    ) -> list[BoundAgentRow]:
        """Return agents bound to a toolkit, paginated by (bound_at DESC, id DESC)."""
        if cursor is not None:
            cursor_ts, cursor_id = cursor
            result = await session.execute(
                text(
                    "SELECT b.id, a.id, a.name, a.status, a.created_at, b.bound_at "
                    "FROM agent_toolkit_bindings b "
                    "JOIN agents a ON a.id = b.agent_id "
                    "WHERE b.toolkit_id = :toolkit_id "
                    "AND (b.bound_at < :cursor_ts "
                    "     OR (b.bound_at = :cursor_ts AND b.id < :cursor_id)) "
                    "ORDER BY b.bound_at DESC, b.id DESC "
                    "LIMIT :limit"
                ),
                {
                    "toolkit_id": toolkit_id,
                    "cursor_ts": cursor_ts,
                    "cursor_id": cursor_id,
                    "limit": limit,
                },
            )
        else:
            result = await session.execute(
                text(
                    "SELECT b.id, a.id, a.name, a.status, a.created_at, b.bound_at "
                    "FROM agent_toolkit_bindings b "
                    "JOIN agents a ON a.id = b.agent_id "
                    "WHERE b.toolkit_id = :toolkit_id "
                    "ORDER BY b.bound_at DESC, b.id DESC "
                    "LIMIT :limit"
                ),
                {"toolkit_id": toolkit_id, "limit": limit},
            )
        return [BoundAgentRow(*row) for row in result.fetchall()]
