"""Trace endpoints scope reads to the calling principal's tenant.

Seed two agents (and a separate toolkit-key tenant), write traces stamped with each,
then verify that GET /traces and GET /traces/{id} only return rows for the caller.
Admins (human sessions) see everything.
"""

import sqlite3

import aiosqlite
import pytest
from src.db import DB_PATH
from src.routers.traces import _trace_scope_clause  # noqa: PLC2701
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_traces_are_scoped_per_principal(app, client, admin_client):  # noqa: ARG001
    """Three rows: agent A's, agent B's, and one for an unrelated toolkit. Each
    principal sees only its own; admin sees all three; an anonymous caller is
    rejected by middleware before reaching the handler.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            """INSERT INTO agents (client_id, client_name, jwks_json, status, created_at)
               VALUES (?, ?, '{}', 'approved', strftime('%s','now'))""",
            [
                ("agnt_trace_a", "trace-a"),
                ("agnt_trace_b", "trace-b"),
            ],
        )
        await db.executemany(
            """INSERT INTO executions
                  (id, toolkit_id, agent_id, status, created_at)
               VALUES (?, ?, ?, 'success', unixepoch())""",
            [
                ("exec_traceA0001", "default", "agnt_trace_a"),
                ("exec_traceB0001", "default", "agnt_trace_b"),
                ("exec_otherTK001", "other_toolkit", None),
            ],
        )
        await db.commit()

    try:
        # Admin sees all three.
        admin_resp = admin_client.get("/traces?limit=500")
        assert admin_resp.status_code == 200
        admin_ids = {t["id"] for t in admin_resp.json()["traces"]}
        assert {"exec_traceA0001", "exec_traceB0001", "exec_otherTK001"} <= admin_ids

        # Build a TestClient impersonating agent A by stamping request.state directly
        # via a thin middleware override would be invasive — instead, we exercise
        # the SQL scope via the helper to keep this test focused on the data path.
        class _Req:
            def __init__(self, **state):
                self.state = type("S", (), state)

        # Agent A: only its own trace returned.
        sql_a, params_a = _trace_scope_clause(
            _Req(is_admin=False, agent_client_id="agnt_trace_a", toolkit_id="default")
        )
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(f"SELECT id FROM executions WHERE {sql_a}", params_a) as cur:
                rows = [r[0] for r in await cur.fetchall()]
        assert rows == ["exec_traceA0001"]

        # Agent B: only its own trace.
        sql_b, params_b = _trace_scope_clause(
            _Req(is_admin=False, agent_client_id="agnt_trace_b", toolkit_id="default")
        )
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(f"SELECT id FROM executions WHERE {sql_b}", params_b) as cur:
                rows = [r[0] for r in await cur.fetchall()]
        assert rows == ["exec_traceB0001"]

        # Toolkit-key caller (no agent_client_id): scoped by toolkit_id, sees both
        # traces tagged with toolkit "other_toolkit" and none of the agent-stamped ones.
        sql_tk, params_tk = _trace_scope_clause(
            _Req(is_admin=False, agent_client_id=None, toolkit_id="other_toolkit")
        )
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(f"SELECT id FROM executions WHERE {sql_tk}", params_tk) as cur:
                rows = [r[0] for r in await cur.fetchall()]
        assert rows == ["exec_otherTK001"]

        # Admin: sees everything.
        sql_admin, params_admin = _trace_scope_clause(_Req(is_admin=True))
        assert sql_admin == "1=1"
        assert params_admin == []

        # Fail-closed branch: no principal at all.
        sql_none, params_none = _trace_scope_clause(
            _Req(is_admin=False, agent_client_id=None, toolkit_id=None)
        )
        assert sql_none == "0=1"
        assert params_none == []
    finally:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM executions WHERE id IN (?, ?, ?)",
                ("exec_traceA0001", "exec_traceB0001", "exec_otherTK001"),
            )
            await db.execute(
                "DELETE FROM agents WHERE client_id IN (?, ?)",
                ("agnt_trace_a", "agnt_trace_b"),
            )
            await db.commit()


def test_traces_endpoint_rejects_anonymous_caller(app):
    """A truly anonymous caller never reaches the trace handler — middleware 401s first."""
    with TestClient(app, raise_server_exceptions=False) as anon:
        assert anon.get("/traces").status_code == 401
        assert anon.get("/traces/exec_doesnotexist").status_code == 401


def test_get_trace_returns_404_for_cross_tenant(app, admin_client, agent_only_client):  # noqa: ARG001
    """Cross-tenant GET /traces/{id} returns 404, not 403, to avoid leaking existence."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            """INSERT INTO executions (id, toolkit_id, agent_id, status, created_at)
               VALUES (?, ?, ?, 'success', unixepoch())""",
            ("exec_xxxxxxxx0042", "isolated_toolkit", None),
        )
        cx.commit()
    try:
        # Admin sees it.
        assert admin_client.get("/traces/exec_xxxxxxxx0042").status_code == 200
        # Agent-only client (different toolkit) gets 404, not 403.
        assert agent_only_client.get("/traces/exec_xxxxxxxx0042").status_code == 404
    finally:
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("DELETE FROM executions WHERE id=?", ("exec_xxxxxxxx0042",))
            cx.commit()
