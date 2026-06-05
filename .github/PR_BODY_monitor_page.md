## Summary

Add a unified **Monitor page** — Overview / Execution Log / Jobs — backed by the `executions` and `jobs` tables, replacing the separate Traces and Jobs pages. The PR also: links every execution to its API catalog entry (`api_id`) and to the job/workflow that spawned it (`job_id` / `parent_trace_id`); persists workflow inputs/outputs/steps so the trace drawer has real detail; adds free-text search and a polished pagination footer to both tables; unifies vendor branding behind a shared registry; and fixes one real **security bug** found along the way (Cookie request-side leak in the broker).

> **Reviewer attention:** the most important change is `fix(security): strip Cookie request header in broker forwards` (`17f5bec`), which closes #457. Recommend reviewing that commit first.

> **Branch state:** merged with `origin/main` at `22186db` to absorb #443/#444/#445 (dep bumps), #447 (Discover + Workspace surfaces), and #458 (axe sweep). Conflict resolution notes are in the merge commit body. Pre-merge tip is preserved at the local tag `ia/monitor-page-pre-merge` for rollback.

## What ships

### Monitor page (UI)

- Three tabs replacing the old `TracesPage` + `JobsPage`:
  - **Overview** — health strip, breakdown by toolkit / API / agent, per-row sparkline trends, daily bar chart, top-N bubble chart, and a clickable **Active-now** pill (hover for detail, click to jump to in-flight jobs)
  - **Execution Log** — paginated trace table with filters (status, toolkit, API, agent, time-range) + **free-text search**, a detail sheet showing inputs/outputs/steps and **child broker calls**, and an inline `JobBadge` when a trace is part of a job
  - **Jobs** — async/workflow jobs with status/kind/toolkit/agent filters + **free-text search**, polling, a detail sheet with cancel, and a back-link to the originating trace
- **Deep-linking** — tab, filters, search (`?q=`), and the open drawer (`?id=` / `?job=`) all live in the URL, so refresh, back/forward, and shared links all restore state
- **Cross-link surface**
  - Trace → job: `JobBadge` in the Execution Log row + a **Linked Context** section in the trace detail sheet
  - Job → trace: clickable `trace_id` in the job detail sheet
  - Workflow → children: a **Child broker calls** panel listing each child trace spawned by the workflow (`parent_trace_id`)
- **`PageHelp`** in the header explains the Execution Log vs Jobs distinction
- **Vendor branding** unified behind a shared `vendor-registry` so the same API renders the same icon/colour across every chart (no more per-chart colour drift)

### Backend surface for Monitor

- `executions` gains `api_id`, `job_id`, `parent_trace_id`, and `inputs`/`outputs` columns + indexes (`alembic/versions/0007_monitor_links.py`; idempotent via `PRAGMA table_info` checks)
- `write_trace` persists the new columns; `UPSERT` uses `COALESCE(existing, excluded)` so partial updates don't clear a cross-link
- `GET /traces` & `GET /jobs` gain a `?q=` free-text filter (case-insensitive `LIKE` across the rendered columns, with `%`/`_` escaped + `ESCAPE '\'`, and a stable `id` ordering tiebreaker)
- `GET /traces/{id}` returns `children[]` (child broker traces) and per-step `inputs`/`outputs`
- `GET /jobs` exposes `parent_trace_id` (correlated lookup) so a child job renders "part of workflow X" without a second fetch; the `kind` filter and comma-separated `status` are supported
- `GET /traces/usage` returns per-row `trend` buckets for the sparklines and tenant-scopes `stats.active_now`
- `broker.py` reads `X-Jentic-Parent-Trace` only from loopback addresses; `workflows.py` threads it onto the arazzo-runner subprocess so child hops auto-attribute to the workflow trace
- API/UI contract aligned: `JobOut.capability` matches the wire (was `slug_or_id`), `TraceStepOut.inputs` matches the emitted step shape, `ui/openapi.json` regenerated

### Security fix — `fix(security)` (`17f5bec`) — closes #457

When a human browser session calls the broker, the browser attaches `Cookie: jentic_session=…` to every request. The broker's `_HOP_BY_HOP` set previously did **not** include `cookie`, so the admin session JWT was forwarded verbatim to the upstream API and — for async dispatch — echoed back into `jobs.result.body`, where any admin reading `GET /jobs/{id}` could harvest it.

I caught this while writing the e2e smoke: the urllib `CookieJar` carried over the admin session, the broker forwarded it to httpbin, httpbin echoed it into the response body, and the broker stored that body in the jobs table.

**Fix**: add `"cookie"` to `_HOP_BY_HOP`. Pinned by `tests/test_broker_header_hygiene.py`, which also pins the `X-Jentic-*` strip behaviour so a careless refactor can't reopen the leak.

This is the request-side counterpart to #56 (response-side, already fixed). Impact is zero for `tk_`-keyed agent traffic (no cookies); browser/admin-session traffic stops leaking the JWT.

### Branch self-review fixes (latest commits)

A read-only review pass over the whole branch surfaced and fixed:

- **API contract drift** — `JobOut` declared `slug_or_id` while the serializer + UI used `capability`; `TraceStepOut` declared a dead `detail` while the wire sent `inputs`. Both realigned; `openapi.json` regenerated (`refactor(api)`, `56f8f57`).
- **`?q=` LIKE injection** — `%`/`_` acted as wildcards (`q=%` matched everything). Escaped + `ESCAPE '\'`; added a stable pagination tiebreaker (`refactor(observe)`, `4f588f5`).
- **Jobs search fired per-keystroke** — threaded the debounced value into the query while keeping the raw value on the controlled input; fixed the clear-flap; gated in-flight log rows behind active filters (`refactor(monitor)`, `ae3ee5c`).
- **HoverTooltip was mouse-only** — made the trigger keyboard-focusable + Escape-to-dismiss (`refactor(ui)`, `2762e9e`).
- **Seed data** — child broker traces now link to their parent workflow trace so `children[]`/parent-link features have data in dev (`chore(seed)`, `579ff1b`).

### Dev tooling

- `scripts/e2e_smoke.py` — real-call probe against `httpbin.org` (no secrets). Fires 6 sync + 3 async broker calls, polls to terminal state, asserts each async row carries the expected `job_id`, then **registers an inline OpenAPI + 2-step Arazzo workflow, runs it, and asserts both child broker traces land with `parent_trace_id == workflow_trace_id`**. Idempotent, ~13s.
- `scripts/seed_monitor_data.py` — `DB_PATH` env overrides the container path for host runs; populates `api_id`, the `apis` catalog, workflow inputs/outputs/steps, and child broker traces.
- `compose.parallel.yml` — isolated docker stack on alternate host ports so Monitor work doesn't disturb the regular dev stack.
- `ui/vite.config.ts` — `/agents` added to the SPA proxy table (was breaking the agents page in dev).

## Diff size

- ~46 commits, **+23k / −10k** lines vs `origin/main` (post-merge)
- Large chunks are the regenerated OpenAPI client + the new Monitor component tree; `TracesPage.tsx` and `JobsPage.tsx` are removed and replaced by `MonitorPage.tsx` + per-tab components

## Test plan

- [x] Backend: full pytest — **612 passed, 1 skipped**. Two environment-only failures: `test_no_auth_api_forwards_without_credentials` (sandbox turns an expected connection-refused into a 60s timeout: 504 vs 502) and a transient `test_openapi_contract` that is **green** after regenerating `ui/openapi.json`.
- [x] Monitor + contract subset re-run clean: **66 passed** (`test_openapi_contract`, `test_monitor_search_q`, `test_traces_children`, `test_jobs_parent_trace`, `test_jobs_filters`, `test_traces_filters`, `test_traces_usage`, `test_traces_api_id_column`, `test_traces_inputs_outputs`)
- [x] Cookie hygiene test verified to fail without the broker fix and pass with it
- [x] Frontend: `tsc --noEmit` clean; ESLint/Prettier clean on touched files (2 pre-existing HoverTooltip a11y warnings remain — can't be cleanly resolved without dropping the arbitrary-children wrapper)
- [x] E2E smoke — green: 6 sync + 3 async, 3/3 jobs `complete`, 3/3 exec↔job cross-links, 2/2 workflow child traces (`parent_trace_id == workflow_trace_id`)
- [ ] **Reviewer to verify**: open `/agents` after a fresh login (regression check for the Vite proxy fix)
- [ ] **Reviewer to verify**: hit the broker from a browser logged in as admin, then `GET /jobs/{recent_id}` and confirm `result.body` contains no `jentic_session=…` substring
- [ ] **Reviewer to verify**: `/discover` and `/workspace` (added by #447) still work after the merge

## Issues

- **Closes #457** — Cookie request header leaked to upstream APIs and into stored job bodies. Fixed and pinned by `tests/test_broker_header_hygiene.py`. This issue was filed during this work, after the e2e smoke surfaced the leak.
- **Related to #56** — response-side header-strip analogue, already closed. This PR is the request-side counterpart.

Issues filed while investigating the codebase during this work but **out of scope** here (separate follow-ups): #452 (split `components/ui/` into primitives vs widgets), #451 (soft-delete leaves toolkits inconsistent), #450 (favicon + meta tags), #446 (Discover stats strip), #440 (persist catalog GitHub URL), #438 (credential health check), #437 (search overhaul).

## Out of scope (follow-ups)

- Real authenticated broker call in `e2e_smoke.py` (e.g. GitHub or OpenAI) — needs secrets in CI; the no-auth httpbin path covers cross-link wiring identically.
- `AgentsPage` should distinguish 401/403 (re-auth) from 5xx / network errors instead of the catch-all "Could not load agents" message that masked the Vite proxy bug.

> Per repo convention, **squash + merge**. The squash subject/body are pre-filled from the PR title and this description.
