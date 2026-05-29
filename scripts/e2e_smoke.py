#!/usr/bin/env python3
"""
End-to-end smoke against a running jentic-mini parallel stack.

Unlike ``seed_monitor_data.py`` (which writes synthetic rows directly into
SQLite), this script exercises the *real* code paths: it logs in as admin,
mints a toolkit API key, calls the broker, and polls async jobs. Every row
it produces in ``executions`` and ``jobs`` was written by the same code that
processes production traffic.

Target: ``httpbin.org`` — chosen because it requires no auth, has stable
public endpoints, and exists in zero catalog setup. The broker's policy gate
falls through to anonymous forwarding for hosts with no credential
configured, so we don't need to register an OAS spec or vault entry.

What it covers:
1. Sync broker calls   → executions row, http_status set, agent_id linked
2. Async broker calls  → jobs row + executions row with cross-link
                         (job.trace_id == trace.id == execution_id)
3. Mixed success/error → at least one 4xx response so the Monitor's
                         "failed" bucket has live data

What it does NOT cover (out of scope for a public-API smoke):
- Workflow execution / parent_trace_id (needs a registered Arazzo workflow)
- Credential injection (none required for httpbin)

Idempotency: re-running the script against the same backend is safe — it
reuses the existing ``e2e-smoke`` toolkit key if one is already labelled,
otherwise mints a fresh one. Existing executions/jobs are left in place;
each run simply appends new rows.

Usage:
    python3 scripts/e2e_smoke.py                       # default :5180
    JENTIC_BASE_URL=http://localhost:8900 python3 …    # alt port
    JENTIC_ADMIN_PASSWORD=… python3 scripts/e2e_smoke.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from typing import Any


DEFAULT_BASE_URL = os.environ.get("JENTIC_BASE_URL", "http://localhost:5180")
ADMIN_USERNAME = os.environ.get("JENTIC_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("JENTIC_ADMIN_PASSWORD", "adminadmin")
TOOLKIT_KEY_LABEL = "e2e-smoke"
SYNC_PROBES = [
    ("GET", "/get", 200),
    ("GET", "/status/200", 200),
    ("GET", "/status/404", 404),
    ("GET", "/status/500", 500),
    ("GET", "/headers", 200),
    ("GET", "/uuid", 200),
]
ASYNC_PROBES = [
    ("GET", "/get", 200),
    ("GET", "/delay/1", 200),
    ("GET", "/status/200", 200),
]
HTTPBIN_HOST = "httpbin.org"


class HTTPClient:
    """Tiny urllib wrapper that holds an admin session cookie + agent key."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookies = CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.opener = opener
        self.agent_key: str | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        use_agent_key: bool = False,
    ) -> tuple[int, dict[str, str], bytes]:
        url = self.base_url + path
        body_bytes: bytes | None = None
        hdrs = {"Accept": "application/json"}
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        if use_agent_key:
            if not self.agent_key:
                raise RuntimeError("agent_key not set — call mint_agent_key() first")
            hdrs["X-Jentic-API-Key"] = self.agent_key
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=body_bytes, method=method, headers=hdrs)
        # Broker calls (`use_agent_key=True`) authenticate as an *agent*, not as
        # an admin browser session. Sending the admin `jentic_session` cookie
        # along would (a) be the wrong identity and (b) currently gets forwarded
        # to upstream by the broker (no Cookie scrubbing) — meaning the admin
        # JWT would land in upstream logs and in the broker's stored job result.
        # Use a one-shot opener with no cookie jar for those requests.
        opener = urllib.request.build_opener() if use_agent_key else self.opener
        try:
            resp = opener.open(req, timeout=30)
            status = resp.status
            resp_headers = dict(resp.headers.items())
            payload = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            resp_headers = dict(exc.headers.items()) if exc.headers else {}
            payload = exc.read() if hasattr(exc, "read") else b""
        return status, resp_headers, payload

    def json_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        use_agent_key: bool = False,
    ) -> tuple[int, dict[str, str], Any]:
        status, hdrs, raw = self.request(
            method, path, json_body=json_body, headers=headers, use_agent_key=use_agent_key
        )
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw.decode(errors="replace")
        return status, hdrs, body


def login_admin(http: HTTPClient) -> None:
    """Authenticate as admin. Required for toolkit/key management endpoints."""
    status, _, body = http.json_request(
        "POST",
        "/user/login",
        json_body={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    if status != 200:
        raise SystemExit(
            f"Admin login failed (HTTP {status}): {body!r}\n"
            f"  base_url={http.base_url}  user={ADMIN_USERNAME}\n"
            f"  hint: set JENTIC_ADMIN_PASSWORD if the admin password is not 'adminadmin'."
        )


def mint_agent_key(http: HTTPClient) -> str:
    """Reuse an existing e2e-smoke key if present, otherwise mint a new one.

    The full key value is only returned at creation time. If a key with our
    label already exists, we cannot retrieve its value — we always mint a
    fresh one. To keep re-runs from accumulating key rows indefinitely, we
    revoke any prior e2e-smoke keys before issuing the new one.
    """
    status, _, body = http.json_request("GET", "/toolkits/default/keys")
    if status == 200 and isinstance(body, dict):
        for key in body.get("keys", []):
            if key.get("label") == TOOLKIT_KEY_LABEL:
                key_id = key.get("id")
                if key_id:
                    http.json_request("DELETE", f"/toolkits/default/keys/{key_id}")
    status, _, body = http.json_request(
        "POST",
        "/toolkits/default/keys",
        json_body={"label": TOOLKIT_KEY_LABEL},
    )
    if status not in (200, 201) or not isinstance(body, dict) or not body.get("key"):
        raise SystemExit(f"Could not mint agent key (HTTP {status}): {body!r}")
    return body["key"]


def fire_sync(http: HTTPClient, method: str, path: str, expected: int) -> dict[str, Any]:
    target = f"/{HTTPBIN_HOST}{path}"
    t0 = time.monotonic()
    status, hdrs, _ = http.request(method, target, use_agent_key=True)
    dt_ms = int((time.monotonic() - t0) * 1000)
    return {
        "target": target,
        "expected": expected,
        "status": status,
        "ok": status == expected,
        "execution_id": hdrs.get("x-jentic-execution-id"),
        "duration_ms": dt_ms,
    }


def fire_async(http: HTTPClient, method: str, path: str) -> dict[str, Any]:
    """Fire with Prefer: respond-async, wait=0 — backend always returns 202.

    The job_id and execution_id come back in response headers; the body is
    a small JSON envelope with a poll URL.
    """
    target = f"/{HTTPBIN_HOST}{path}"
    status, hdrs, _ = http.request(
        method,
        target,
        headers={"Prefer": "respond-async, wait=0"},
        use_agent_key=True,
    )
    return {
        "target": target,
        "status": status,
        "job_id": hdrs.get("x-jentic-job-id"),
        "execution_id": hdrs.get("x-jentic-execution-id"),
    }


def poll_job(http: HTTPClient, job_id: str, timeout_s: float = 15.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status, _, body = http.json_request("GET", f"/jobs/{job_id}")
        if status != 200 or not isinstance(body, dict):
            return {"job_id": job_id, "status": "lookup_failed", "http": status, "body": body}
        last = body
        if body.get("status") in ("complete", "failed", "cancelled"):
            return body
        time.sleep(0.5)
    return {**last, "status": last.get("status", "timeout"), "_timed_out": True}


def assert_trace_link(http: HTTPClient, trace_id: str, expected_job_id: str) -> dict[str, Any]:
    """Confirm the executions row carries the cross-link to its parent job."""
    status, _, body = http.json_request("GET", f"/traces/{trace_id}")
    return {
        "http": status,
        "trace_id": body.get("id") if isinstance(body, dict) else None,
        "job_id": body.get("job_id") if isinstance(body, dict) else None,
        "expected_job_id": expected_job_id,
        "matches": isinstance(body, dict) and body.get("job_id") == expected_job_id,
    }


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    parser = argparse.ArgumentParser(description="jentic-mini parallel stack e2e smoke")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument(
        "--skip-async", action="store_true", help="Skip the async broker calls + job polling"
    )
    args = parser.parse_args()

    http = HTTPClient(args.base_url)

    section("Setup")
    login_admin(http)
    print(f"  logged in as {ADMIN_USERNAME} on {http.base_url}")
    http.agent_key = mint_agent_key(http)
    print(f"  minted agent key  prefix={http.agent_key[:6]}…  label={TOOLKIT_KEY_LABEL}")

    section("Sync broker calls")
    sync_results = []
    for method, path, expected in SYNC_PROBES:
        result = fire_sync(http, method, path, expected)
        sync_results.append(result)
        marker = "ok " if result["ok"] else "ERR"
        print(
            f"  [{marker}] {method:4s} {result['target']:38s} "
            f"got={result['status']} (expected {expected})  "
            f"trace={result['execution_id'] or '(missing)'}  {result['duration_ms']}ms"
        )

    sync_failures = [r for r in sync_results if not r["ok"]]
    if sync_failures:
        print(f"  WARN: {len(sync_failures)} sync probe(s) returned unexpected status")

    async_results = []
    if not args.skip_async:
        section("Async broker calls (Prefer: respond-async, wait=0)")
        for method, path, _expected in ASYNC_PROBES:
            r = fire_async(http, method, path)
            async_results.append(r)
            print(
                f"  dispatched {method} {r['target']:30s} "
                f"job={r['job_id'] or '(missing)'}  trace={r['execution_id'] or '(missing)'}"
            )

        section("Polling jobs to terminal state")
        terminal_results = []
        for r in async_results:
            if not r["job_id"]:
                continue
            terminal = poll_job(http, r["job_id"])
            terminal_results.append({"dispatch": r, "terminal": terminal})
            print(
                f"  job {r['job_id']:24s} → status={terminal.get('status')} "
                f"trace_id={terminal.get('trace_id') or '(missing)'}"
            )

        section("Verifying execution↔job cross-links")
        link_failures = 0
        for entry in terminal_results:
            r = entry["dispatch"]
            if not (r["execution_id"] and r["job_id"]):
                link_failures += 1
                print(f"  MISSING trace or job id from dispatch: {r}")
                continue
            check = assert_trace_link(http, r["execution_id"], r["job_id"])
            if check["matches"]:
                print(f"  ok  trace {r['execution_id']} → job_id={r['job_id']}")
            else:
                link_failures += 1
                print(f"  ERR trace {r['execution_id']}: {check}")
        if link_failures:
            print(f"  FAIL: {link_failures} cross-link check(s) failed")

    section("Summary")
    print(f"  base_url       : {http.base_url}")
    print(f"  sync probes    : {len(sync_results)} ({len(sync_failures)} unexpected)")
    print(f"  async probes   : {len(async_results)}")
    monitor_url = http.base_url.replace(":5180", ":5181") + "/monitor"
    print(f"  monitor page   : {monitor_url}")
    print(f"  agents page    : {monitor_url.rsplit('/', 1)[0]}/agents")

    if sync_failures or (not args.skip_async and any(not r.get("job_id") for r in async_results)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
