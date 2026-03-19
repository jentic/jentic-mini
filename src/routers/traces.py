"""
Execution trace endpoints.

Every execution (operation or workflow) writes a trace record.
Callers can look up trace details — especially useful when a workflow fails,
to inspect step-by-step results and see which step caused the error.

Routes:
  GET /traces             list recent execution traces (paginated)
  GET /traces/{id}        full trace with step-level detail
"""
import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from src.db import get_db
from src.models import TraceOut, TraceListPage

router = APIRouter()


# ── DB helpers ────────────────────────────────────────────────────────────────

async def write_trace(
    *,
    trace_id: str,
    toolkit_id: str | None,
    operation_id: str | None,
    workflow_id: str | None,
    spec_path: str | None,
    status: str,
    http_status: int | None,
    duration_ms: int | None,
    error: str | None,
    step_outputs: dict | None = None,
) -> str:
    """Write an execution trace (+ optional step records) to the DB."""
    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO executions
               (id, toolkit_id, operation_id, workflow_id, spec_path,
                status, http_status, duration_ms, error, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,unixepoch())""",
            (trace_id, toolkit_id, operation_id, workflow_id, spec_path,
             status, http_status, duration_ms, error),
        )

        if step_outputs:
            for step_id, step_data in step_outputs.items():
                err_ctx = step_data.get("runner_error_context") if isinstance(step_data, dict) else None
                step_http = err_ctx.get("http_code") if isinstance(err_ctx, dict) else None
                step_err = step_data.get("error") if isinstance(step_data, dict) else None
                await db.execute(
                    """INSERT INTO execution_steps
                       (id, execution_id, step_id, http_status, output, error)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        trace_id,
                        step_id,
                        step_http,
                        json.dumps(step_data),
                        step_err,
                    ),
                )
        await db.commit()
    return trace_id


def new_trace_id() -> str:
    return "exec_" + uuid.uuid4().hex[:12]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/traces", summary="List execution traces — audit recent broker and workflow calls", response_model=TraceListPage)
async def list_traces(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Returns recent execution traces with status, capability id, toolkit, timestamp, and HTTP status. Use GET /traces/{trace_id} for step-level detail."""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, toolkit_id, operation_id, workflow_id,
                      status, http_status, duration_ms, error, created_at, completed_at
               FROM executions
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()
        async with db.execute("SELECT COUNT(*) FROM executions") as cur:
            total = (await cur.fetchone())[0]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "traces": [
            {
                "id": r[0],
                "toolkit_id": r[1],
                "operation_id": r[2],
                "workflow_id": r[3],
                "status": r[4],
                "http_status": r[5],
                "duration_ms": r[6],
                "error": r[7],
                "created_at": r[8],
                "completed_at": r[9],
                "_links": {"self": f"/traces/{r[0]}"},
            }
            for r in rows
        ],
    }


@router.get("/traces/{trace_id}", summary="Get trace detail — step-by-step execution log", response_model=TraceOut)
async def get_trace(trace_id: str):
    """Returns the full execution trace with all steps: capability called, inputs, outputs, HTTP status, and timing. Useful for debugging failed workflow steps."""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, toolkit_id, operation_id, workflow_id, spec_path,
                      status, http_status, duration_ms, error, created_at, completed_at
               FROM executions WHERE id=?""",
            (trace_id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(404, f"Trace '{trace_id}' not found")

        async with db.execute(
            """SELECT id, step_id, operation, status, http_status,
                      inputs, output, error, started_at, completed_at
               FROM execution_steps WHERE execution_id=? ORDER BY started_at""",
            (trace_id,),
        ) as cur:
            step_rows = await cur.fetchall()

    steps = [
        {
            "id": s[0],
            "step_id": s[1],
            "operation": s[2],
            "status": s[3],
            "http_status": s[4],
            "output": json.loads(s[5]) if s[5] else None,  # inputs stored in output col
            "detail": json.loads(s[6]) if s[6] else None,
            "error": s[7],
            "started_at": s[8],
            "completed_at": s[9],
        }
        for s in step_rows
    ]

    return {
        "id": row[0],
        "toolkit_id": row[1],
        "operation_id": row[2],
        "workflow_id": row[3],
        "spec_path": row[4],
        "status": row[5],
        "http_status": row[6],
        "duration_ms": row[7],
        "error": row[8],
        "created_at": row[9],
        "completed_at": row[10],
        "steps": steps,
        "_links": {"self": f"/traces/{row[0]}"},
    }
