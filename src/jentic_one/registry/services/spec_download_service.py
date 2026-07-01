"""Spec download service — retrieve stored OpenAPI spec content for revisions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from jentic_one.registry.repos.api_repo import ApiRepository
from jentic_one.registry.repos.revision_repo import ApiRevisionRepository
from jentic_one.registry.repos.spec_file_repo import SpecFileRepository
from jentic_one.registry.services.errors import (
    ApiNotFoundError,
    NoCurrentRevisionError,
    RevisionNotFoundError,
    SpecFileMissingError,
)
from jentic_one.shared.context import Context


@dataclass(frozen=True)
class SpecDocument:
    """Resolved spec document ready for serialisation."""

    content: dict[str, Any]
    filename_stem: str


class SpecDownloadService:
    """Retrieve the raw OpenAPI spec content for an API revision."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def get_live_spec(self, vendor: str, name: str, version: str) -> SpecDocument:
        async with self._ctx.registry_db.session() as session:
            api = await ApiRepository.get_by_identifier_with_current_revision(
                session, vendor, name, version
            )
            if api is None:
                raise ApiNotFoundError(vendor, name, version)
            if api.current_revision_id is None:
                raise NoCurrentRevisionError(vendor, name, version)

            spec_file = await SpecFileRepository.get_for_revision(session, api.current_revision_id)
            if spec_file is None:
                raise SpecFileMissingError(str(api.current_revision_id))

        return SpecDocument(
            content=spec_file.content,
            filename_stem=f"{vendor}-{name}-{version}",
        )

    async def get_revision_spec(
        self, vendor: str, name: str, version: str, revision_id: str
    ) -> SpecDocument:
        try:
            revision_uuid = uuid.UUID(revision_id)
        except ValueError:
            raise RevisionNotFoundError(revision_id, vendor, name, version) from None

        async with self._ctx.registry_db.session() as session:
            api = await ApiRepository.get_by_identifier(session, vendor, name, version)
            if api is None:
                raise ApiNotFoundError(vendor, name, version)

            revision = await ApiRevisionRepository.get_for_api(session, api.id, revision_uuid)
            if revision is None:
                raise RevisionNotFoundError(revision_id, vendor, name, version)

            spec_file = await SpecFileRepository.get_for_revision(session, revision.id)
            if spec_file is None:
                raise SpecFileMissingError(revision_id)

        return SpecDocument(
            content=spec_file.content,
            filename_stem=f"{vendor}-{name}-{version}",
        )
