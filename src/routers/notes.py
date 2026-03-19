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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db import get_db

router = APIRouter(prefix="/notes")


class NoteCreate(BaseModel):
    """
    Create a note on any Jentic resource.

    resource: the resource identifier (operation_id, api_id, workflow slug)
    type: categorize the note for filtering and analysis
    note: the content — be specific and actionable
    execution_id: link to a specific execution (optional)
    confidence: how certain are you?
    source: where did you observe this?
    """
    resource: str
    type: str | None = None   # 'auth_quirk' | 'usage_hint' | 'execution_feedback' | 'correction'
    note: str
    execution_id: str | None = None
    confidence: str | None = None   # 'observed' | 'suspected' | 'verified'
    source: str | None = None       # e.g. 'test run', 'production', 'documentation'


@router.post("", status_code=201, summary="Add a note — annotate a capability with feedback or a correction")
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


@router.get("", summary="List notes for a resource")
async def list_notes(resource: str | None = None, type: str | None = None, limit: int = 50):
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


@router.delete("/{note_id}", status_code=204, summary="Delete a note")
async def delete_note(note_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        await db.commit()
