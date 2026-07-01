"""Repository for AgentToolkitBinding CRUD."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.admin.core.schema.agent_toolkit_bindings import AgentToolkitBinding


class AgentToolkitBindingRepository:
    """Data access layer for AgentToolkitBinding entities — flush-only, never commits."""

    @staticmethod
    async def bind(
        session: AsyncSession,
        *,
        agent_id: str,
        toolkit_id: str,
        created_by: str,
    ) -> AgentToolkitBinding:
        binding = AgentToolkitBinding(
            agent_id=agent_id, toolkit_id=toolkit_id, created_by=created_by
        )
        session.add(binding)
        await session.flush()
        return binding

    @staticmethod
    async def unbind(session: AsyncSession, *, agent_id: str, toolkit_id: str) -> bool:
        stmt = (
            delete(AgentToolkitBinding)
            .where(AgentToolkitBinding.agent_id == agent_id)
            .where(AgentToolkitBinding.toolkit_id == toolkit_id)
        )
        result = await session.execute(stmt)
        await session.flush()
        return int(result.rowcount) > 0  # type: ignore[attr-defined]

    @staticmethod
    async def list_for_agent(session: AsyncSession, agent_id: str) -> list[AgentToolkitBinding]:
        stmt = (
            select(AgentToolkitBinding)
            .where(AgentToolkitBinding.agent_id == agent_id)
            .order_by(AgentToolkitBinding.bound_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete_for_agent(session: AsyncSession, agent_id: str) -> int:
        stmt = delete(AgentToolkitBinding).where(AgentToolkitBinding.agent_id == agent_id)
        result = await session.execute(stmt)
        await session.flush()
        return int(result.rowcount)  # type: ignore[attr-defined]
