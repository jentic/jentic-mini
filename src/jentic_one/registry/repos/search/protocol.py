"""Search protocol and result types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A single search match for an operation."""

    operation_id: str
    revision_id: uuid.UUID
    api_id: uuid.UUID
    distance: float
    score: float | None = None


@dataclass(frozen=True, slots=True)
class SearchCursor:
    """Keyset cursor encoding (distance, operation_id) for tie-breaking."""

    distance: float
    operation_id: str


@runtime_checkable
class SearchStrategy(Protocol):
    """Strategy protocol for pluggable search modes.

    Each strategy declares its mode name and target dialect.
    """

    name: str
    dialect: str

    async def search_operations(
        self,
        session: AsyncSession,
        *,
        query: str,
        api_filters: list[uuid.UUID] | None = None,
        revision_pins: dict[uuid.UUID, uuid.UUID] | None = None,
        limit: int = 20,
        cursor: SearchCursor | None = None,
    ) -> list[SearchHit]:
        """Return operations ordered by ascending distance/dissimilarity."""
        ...
