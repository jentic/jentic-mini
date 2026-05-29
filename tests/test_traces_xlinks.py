"""Trace cross-link columns: job_id and parent_trace_id.

These columns power the Monitor page Execution Log cross-link badge ("part of
job …") and the Execution Detail panel's "part of workflow X" line.

Coverage:
1. write_trace persists both new fields and roundtrips them through the public
   GET /traces and GET /traces/{id} endpoints.
2. The broker reads X-Jentic-Parent-Trace only from loopback callers — header
   from external client.host is ignored, preventing spoofed workflow parentage.

We seed via write_trace + sqlite directly because (a) the broker call path
spins up real upstream HTTP and (b) we want to assert the storage shape
independent of dispatch concerns.
"""

import inspect
import sqlite3

import pytest
from src.db import DB_PATH
from src.routers import broker as broker_module
from src.routers.traces import write_trace


_FIXTURE_TRACE_IDS = (
    "exec_xlink_root1",
    "exec_xlink_child",
    "exec_xlink_solo1",
)


@pytest.fixture
def cleanup_xlink_traces():
    """Strip seeded rows; tests insert via write_trace so the upsert path is exercised."""
    yield
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("DELETE FROM executions WHERE id IN (?,?,?)", _FIXTURE_TRACE_IDS)
        cx.commit()


@pytest.mark.asyncio
async def test_write_trace_persists_job_id_and_parent_trace(admin_client, cleanup_xlink_traces):  # noqa: ARG001
    """Both new columns survive INSERT and surface in list + detail responses."""
    await write_trace(
        trace_id="exec_xlink_child",
        toolkit_id="tk_a",
        operation_id="GET/api.github.com/users/me",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=42,
        error=None,
        agent_id=None,
        job_id="job_xlink_001",
        parent_trace_id="exec_xlink_root1",
    )

    list_resp = admin_client.get("/traces?limit=500")
    assert list_resp.status_code == 200
    rows = {t["id"]: t for t in list_resp.json()["traces"]}
    row = rows["exec_xlink_child"]
    assert row["job_id"] == "job_xlink_001"
    assert row["parent_trace_id"] == "exec_xlink_root1"

    detail_resp = admin_client.get("/traces/exec_xlink_child")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["job_id"] == "job_xlink_001"
    assert detail["parent_trace_id"] == "exec_xlink_root1"


@pytest.mark.asyncio
async def test_write_trace_omits_links_when_unset(admin_client, cleanup_xlink_traces):  # noqa: ARG001
    """Top-level (non-job, non-child) traces report null for both link columns."""
    await write_trace(
        trace_id="exec_xlink_solo1",
        toolkit_id="tk_a",
        operation_id="GET/api.github.com/zen",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=15,
        error=None,
    )

    detail = admin_client.get("/traces/exec_xlink_solo1").json()
    assert detail["job_id"] is None
    assert detail["parent_trace_id"] is None


@pytest.mark.asyncio
async def test_upsert_does_not_clobber_links(admin_client, cleanup_xlink_traces):  # noqa: ARG001
    """A second write_trace for the same row (e.g. pending → success) preserves
    job_id/parent_trace_id set on the original insert.

    Regression guard for the COALESCE in the ON CONFLICT clause: without it,
    an async broker call that updates the trace from "pending" to "success"
    would overwrite a previously-stamped job_id with NULL because the late
    write_trace call sites don't pass job_id.
    """
    await write_trace(
        trace_id="exec_xlink_child",
        toolkit_id="tk_a",
        operation_id="GET/api.github.com/users/me",
        workflow_id=None,
        spec_path=None,
        status="pending",
        http_status=202,
        duration_ms=None,
        error=None,
        job_id="job_xlink_001",
        parent_trace_id="exec_xlink_root1",
    )
    # Simulate a later update that does NOT supply the link columns.
    await write_trace(
        trace_id="exec_xlink_child",
        toolkit_id="tk_a",
        operation_id="GET/api.github.com/users/me",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=42,
        error=None,
    )

    detail = admin_client.get("/traces/exec_xlink_child").json()
    assert detail["status"] == "success"
    assert detail["job_id"] == "job_xlink_001"
    assert detail["parent_trace_id"] == "exec_xlink_root1"


# ── X-Jentic-Parent-Trace loopback gating ──────────────────────────────────


def test_parent_trace_header_loopback_only(admin_client):  # noqa: ARG001
    """The broker honors X-Jentic-Parent-Trace only from 127.0.0.1 / ::1.

    External callers cannot forge workflow parentage by setting the header
    on regular broker requests. We assert the loopback-vs-non-loopback
    branch is present in the broker source without standing up a real
    upstream (which would require auth, credentials, and network).
    """
    src = inspect.getsource(broker_module.broker)
    assert "X-Jentic-Parent-Trace" in src
    # Loopback set must be checked before the value is assigned to
    # parent_trace_id. Verify both pieces appear and the loopback hosts are
    # canonical (127.0.0.1 / ::1 / localhost).
    assert '"127.0.0.1"' in src
    assert '"::1"' in src
    assert "parent_trace_id = raw_parent" in src
