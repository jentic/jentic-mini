"""Notes router — agent feedback and knowledge accumulation.

Agents can leave structured notes on any resource (operation, API, workflow).
This feeds the Jentic knowledge base:
- auth_quirk: documents non-standard auth requirements found in the wild
- usage_hint: tips for using an operation effectively
- execution_feedback: what happened when the operation was called
- correction: corrects something in the operation description

Notes are observable by Jentic to improve canonical OpenAPI specs.
"""
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel, Field
from src.validators import NormModel, NormStr

from src.db import get_db
from src.openapi_helpers import agent_hints

router = APIRouter(prefix="/notes")


class NoteCreate(NormModel):
    """Create a note on any Jentic resource for knowledge accumulation and catalog improvement."""
    resource: str = Field(description="Resource identifier: operation_id (METHOD/host/path), api_id, or workflow slug")
    type: NormStr | None = Field(default=None, description="Note category: 'auth_quirk', 'usage_hint', 'execution_feedback', or 'correction'")
    note: str = Field(description="Note content — be specific and actionable")
    execution_id: str | None = Field(default=None, description="Link to specific execution for context (optional)")
    confidence: NormStr | None = Field(default=None, description="Confidence level: 'observed', 'suspected', or 'verified'")
    source: str | None = Field(default=None, description="Observation source, e.g. 'test run', 'production', 'documentation'")


@router.post(
    "",
    status_code=201,
    summary="Add a note — annotate a capability with feedback or a correction",
    openapi_extra={
        **agent_hints(
            when_to_use="Use to report observations about operations, workflows, or APIs that could improve the catalog: auth quirks (non-standard auth requirements), usage hints (tips for effective use), execution feedback (what happened when called), corrections (errors in spec descriptions). Notes feed the Jentic knowledge base for catalog improvement. Link to execution_id for context.",
            prerequisites=[
                "Requires authentication (toolkit key or human session)",
                "Valid resource identifier (operation_id, api_id, or workflow slug)"
            ],
            avoid_when="Do not use for private execution logs — use GET /traces instead. Do not use for credential issues — fix credentials via PATCH /credentials.",
            related_operations=[
                "GET /notes — list existing notes for a resource to avoid duplicates",
                "DELETE /notes/{id} — remove outdated or incorrect notes",
                "GET /traces/{id} — link to execution context when reporting feedback",
                "POST /apis/{api_id}/overlays — submit OpenAPI overlay to fix spec issues"
            ]
        ),
        "requestBody": {"description": "Note details: resource ID, note type (auth_quirk/usage_hint/execution_feedback/correction), content, optional execution link, confidence level, and source"}
    },
)
async def create_note(body: NoteCreate):
    """Attaches a note to any capability (operation, workflow, or API). Use to report auth corrections, schema errors, or updated Arazzo workflows. Notes feed back into the catalog improvement loop."""
    note_id = "note_" + str(uuid.uuid4())[:8]
    async with get_db() as db:
        await db.execute(
            """INSERT INTO notes (id, resource, type, note, execution_id, confidence, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (note_id, body.resource, body.type, body.note,
             body.execution_id, body.confidence, body.source, time.time())
        )
        await db.commit()
    return {"id": note_id, "resource": body.resource, "type": body.type, "created_at": time.time()}


@router.get(
    "",
    summary="List notes for a resource",
    openapi_extra=agent_hints(
        when_to_use="Use to retrieve operational knowledge about operations, workflows, or APIs before calling them. Returns notes from previous executions: auth quirks, usage tips, failure patterns, schema corrections. Filter by ?resource={capability_id} to see notes for a specific operation/workflow, or by ?type={category} to filter by note type (auth_quirk, usage_hint, execution_feedback, correction). Limit defaults to 50, ordered by creation date descending.",
        prerequisites=["Requires authentication (toolkit key or human session)"],
        avoid_when="Do not use for execution history — use GET /traces instead. Do not use for credential status — use GET /credentials.",
        related_operations=[
            "POST /notes — add a note after discovering new operational knowledge",
            "DELETE /notes/{id} — remove outdated notes",
            "GET /inspect/{id} — inspect operation schema before checking notes",
            "GET /traces — view execution history for context"
        ]
    ),
)
async def list_notes(
    resource: Annotated[str | None, Query(description="Filter notes by resource ID (capability_id, api_id, or workflow slug)")] = None,
    type: Annotated[str | None, Query(description="Filter notes by type (auth_quirk, usage_hint, execution_feedback, correction)")] = None,
    limit: Annotated[int, Query(description="Maximum number of notes to return (1-500)", ge=1, le=500)] = 50,
):
    """
    List notes attached to resources (operations, workflows, APIs).

    Notes capture observations from execution — success signals, failure patterns,
    data validation findings, and human annotations. Agents use notes to build
    operational knowledge and improve reliability over time.

    Filter by `?resource={id}` to see notes for a specific operation/workflow,
    or by `?type={type}` to filter by note category (e.g., "success", "error", "validation").
    """
    conditions = []
    params = []
    if resource:
        conditions.append("resource=?")
        params.append(resource)
    if type:
        conditions.append("type=?")
        params.append(type)
    params.append(limit)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with get_db() as db:
        async with db.execute(
            f"""SELECT id, resource, type, note, execution_id, confidence, source, created_at
               FROM notes {where} ORDER BY created_at DESC LIMIT ?""",
            params
        ) as cur:
            rows = await cur.fetchall()

    return [
        {"id": r[0], "resource": r[1], "type": r[2], "note": r[3],
         "execution_id": r[4], "confidence": r[5], "source": r[6], "created_at": r[7]}
        for r in rows
    ]


@router.delete(
    "/{note_id}",
    status_code=204,
    summary="Delete a note",
    openapi_extra=agent_hints(
        when_to_use="Use to remove outdated observations, incorrect annotations, or notes that no longer apply after an API change. Deletion is permanent.",
        prerequisites=[
            "Requires authentication (toolkit key or human session)",
            "Valid note ID from GET /notes (format: note_{8chars})"
        ],
        avoid_when="Do not use to hide execution errors — fix the underlying issue instead. Do not delete notes from other users without coordination.",
        related_operations=[
            "GET /notes — list notes to find the note_id",
            "POST /notes — add a replacement note after deleting an incorrect one"
        ]
    ),
)
async def delete_note(note_id: Annotated[str, Path(description="Note ID to delete (format: note_{8chars})")]):
    """
    Permanently delete a note.

    Use this to remove outdated observations, incorrect annotations, or
    notes that no longer apply after an API change.
    """
    async with get_db() as db:
        await db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        await db.commit()
