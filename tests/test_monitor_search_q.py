"""Free-text `?q=` filter on GET /traces and GET /jobs.

Powers the Monitor's search input. Substring match (case-insensitive via
SQLite default LIKE collation) across the columns the row renders, so
typing `github` matches whether it landed in `api_id`, `operation_id`,
`workflow_id`, or `agent_id` (traces) / `slug_or_id`, `agent_id`,
`toolkit_id`, `upstream_job_url` (jobs).

Whitespace-only inputs are treated as not set so the no-filter plan
stays cheap — the UI sends `q=` whenever the user clears the search.
"""

import sqlite3
import uuid

import pytest
from src.db import DB_PATH
from src.routers.traces import write_trace


@pytest.fixture
def cleanup_q_rows():
    yield
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("DELETE FROM jobs WHERE id LIKE 'job_q_%'")
        cx.execute("DELETE FROM executions WHERE id LIKE 'exec_q_%'")
        cx.commit()


@pytest.mark.asyncio
async def test_traces_q_matches_api_id_substring(admin_client, cleanup_q_rows):  # noqa: ARG001
    target = f"exec_q_{uuid.uuid4().hex[:8]}"
    other = f"exec_q_{uuid.uuid4().hex[:8]}"

    await write_trace(
        trace_id=target,
        toolkit_id="default",
        operation_id="GET/api.github.com/repos/{owner}/{repo}",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=10,
        error=None,
        api_id="github.com",
    )
    await write_trace(
        trace_id=other,
        toolkit_id="default",
        operation_id="GET/api.stripe.com/v1/charges",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=10,
        error=None,
        api_id="stripe.com",
    )

    resp = admin_client.get("/traces?q=github&limit=500")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()["traces"]}
    assert target in ids
    assert other not in ids


@pytest.mark.asyncio
async def test_traces_q_matches_workflow_id(admin_client, cleanup_q_rows):  # noqa: ARG001
    """Workflow trace where the substring lives only in workflow_id."""
    wf = f"exec_q_{uuid.uuid4().hex[:8]}"
    await write_trace(
        trace_id=wf,
        toolkit_id="default",
        operation_id=None,
        workflow_id="wf_review_pr",
        spec_path="github.com/review.arazzo.json",
        status="success",
        http_status=None,
        duration_ms=900,
        error=None,
    )

    resp = admin_client.get("/traces?q=review_pr&limit=500")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()["traces"]}
    assert wf in ids


@pytest.mark.asyncio
async def test_traces_q_is_case_insensitive(admin_client, cleanup_q_rows):  # noqa: ARG001
    """SQLite LIKE is case-insensitive for ASCII by default — verify."""
    target = f"exec_q_{uuid.uuid4().hex[:8]}"
    await write_trace(
        trace_id=target,
        toolkit_id="default",
        operation_id="GET/api.github.com/repos/{owner}/{repo}",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=10,
        error=None,
        api_id="github.com",
    )

    resp = admin_client.get("/traces?q=GitHub&limit=500")
    ids = {r["id"] for r in resp.json()["traces"]}
    assert target in ids


@pytest.mark.asyncio
async def test_traces_q_blank_string_is_ignored(admin_client, cleanup_q_rows):  # noqa: ARG001
    """Whitespace-only `q` short-circuits — same plan as no `q` at all.

    The UI sends `q=` (or `q=   `) on clear; we don't want that to silently
    filter to zero rows on a string the SQL would happily LIKE against.
    """
    target = f"exec_q_{uuid.uuid4().hex[:8]}"
    await write_trace(
        trace_id=target,
        toolkit_id="default",
        operation_id="GET/api.github.com/zen",
        workflow_id=None,
        spec_path=None,
        status="success",
        http_status=200,
        duration_ms=10,
        error=None,
    )

    # `q=%20%20` (two spaces) — pydantic min_length=1 lets it through; the
    # router's .strip() then treats it as unset.
    resp = admin_client.get("/traces?q=%20%20&limit=500")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()["traces"]}
    assert target in ids


@pytest.mark.asyncio
async def test_jobs_q_matches_slug_or_upstream_url(admin_client, cleanup_q_rows):  # noqa: ARG001
    target_slug = f"job_q_{uuid.uuid4().hex[:8]}"
    target_upstream = f"job_q_{uuid.uuid4().hex[:8]}"
    other = f"job_q_{uuid.uuid4().hex[:8]}"

    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            """INSERT INTO jobs (id, kind, slug_or_id, toolkit_id, status, created_at)
               VALUES (?, 'workflow', 'wf_github_review', 'default', 'complete',
                       strftime('%s','now'))""",
            (target_slug,),
        )
        cx.execute(
            """INSERT INTO jobs (id, kind, slug_or_id, toolkit_id, status,
                                 upstream_job_url, created_at)
               VALUES (?, 'broker', 'POST /api.example.com/render', 'default',
                       'upstream_async',
                       'https://example.com/jobs/zzz-github-99', strftime('%s','now'))""",
            (target_upstream,),
        )
        cx.execute(
            """INSERT INTO jobs (id, kind, slug_or_id, toolkit_id, status, created_at)
               VALUES (?, 'broker', 'POST /api.stripe.com/charges', 'default', 'complete',
                       strftime('%s','now'))""",
            (other,),
        )
        cx.commit()

    resp = admin_client.get("/jobs?q=github&limit=100")
    assert resp.status_code == 200
    ids = {row["job_id"] for row in resp.json()["data"]}
    assert target_slug in ids
    assert target_upstream in ids
    assert other not in ids
