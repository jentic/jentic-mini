"""Toolkit binding checker using the admin DB directly."""

from __future__ import annotations

from sqlalchemy import text

from jentic_one.shared.db import DatabaseSession

_BINDING_EXISTS_STMT = text(
    "SELECT 1 FROM agent_toolkit_bindings"
    " WHERE agent_id = :agent_id AND toolkit_id = :toolkit_id"
    " LIMIT 1"
)


class ToolkitBindingChecker:
    """Checks agent→toolkit bindings via direct DB query on admin schema.

    Uses the admin database session to query `agent_toolkit_bindings` without
    importing from the admin module — the query is simple enough to express inline.
    """

    def __init__(self, admin_db: DatabaseSession) -> None:
        self._admin_db = admin_db

    async def has_binding(self, agent_id: str, toolkit_id: str) -> bool:
        """Return True if the agent has a binding to the specified toolkit."""
        async with self._admin_db.session() as session:
            result = await session.execute(
                _BINDING_EXISTS_STMT, {"agent_id": agent_id, "toolkit_id": toolkit_id}
            )
            return result.scalar_one_or_none() is not None
