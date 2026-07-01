"""Repository for SpecFile entities."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.registry.core.schema.spec_files import SpecFile


class SpecFileRepository:
    """Data access layer for SpecFile entities — flush-only, never commits."""

    @staticmethod
    async def get_for_revision(session: AsyncSession, revision_id: uuid.UUID) -> SpecFile | None:
        # Ingest currently stores a single primary spec file per revision. The
        # schema permits multiple (unique per filename), so order by filename to
        # keep selection deterministic if multi-file imports are ever added.
        result = await session.execute(
            select(SpecFile)
            .where(SpecFile.revision_id == revision_id)
            .order_by(SpecFile.filename)
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_or_update(
        session: AsyncSession,
        *,
        revision_id: uuid.UUID,
        filename: str,
        content: dict[str, Any],
        sha: str | None = None,
        source_id: str | None = None,
        created_by: str,
    ) -> SpecFile:
        result = await session.execute(
            select(SpecFile).where(
                SpecFile.revision_id == revision_id, SpecFile.filename == filename
            )
        )
        spec_file = result.scalar_one_or_none()
        if spec_file is not None:
            spec_file.content = content
            spec_file.sha = sha
            spec_file.source_id = source_id
        else:
            spec_file = SpecFile(
                revision_id=revision_id,
                filename=filename,
                content=content,
                sha=sha,
                source_id=source_id,
                created_by=created_by,
            )
            session.add(spec_file)
        await session.flush()
        return spec_file
