"""Pipeline stage that builds the lexical search text for operations."""

from __future__ import annotations

import asyncio
import uuid
from typing import ClassVar

import structlog

from jentic_one.registry.ingest.embeddings.projections import get_projection
from jentic_one.registry.ingest.observability import search_text_size, tracer
from jentic_one.registry.ingest.pipeline.ctx import PipelineContext
from jentic_one.registry.ingest.stages.base import BasePipelineStage
from jentic_one.registry.repos.operation_repo import OperationRepository

logger = structlog.get_logger(__name__)


class BuildSearchTextForOperationsStage(BasePipelineStage):
    """Build and store the lexical search text for every operation in the revision."""

    name: ClassVar[str] = "BuildSearchTextForOperationsStage"
    _requires: ClassVar[dict[str, type]] = {
        "operation_ids": set,
        "revision_id": uuid.UUID,
    }
    _produces: ClassVar[dict[str, type]] = {"operation_search_text_set": bool}

    async def _run(self, ctx: PipelineContext) -> None:
        operation_ids: set[str] = ctx.require("operation_ids", set)

        if not operation_ids:
            ctx.produce("operation_search_text_set", True, bool)
            return

        operations = await OperationRepository.get_by_ids(ctx.session, operation_ids)
        if not operations:
            ctx.produce("operation_search_text_set", True, bool)
            return

        identifier = ctx.specification.api_identifier
        vendor_id = identifier.vendor
        api_name = identifier.name

        projection = get_projection()

        with tracer.start_as_current_span("ingest.build_search_text"):
            texts = await asyncio.to_thread(
                lambda: {
                    op.id: projection.create_projection(op, vendor_id, api_name)
                    for op in operations
                }
            )
            search_text_size.record(sum(len(t) for t in texts.values()))

        await OperationRepository.set_search_text(ctx.session, texts)
        ctx.produce("operation_search_text_set", True, bool)
