# Phase 25 Plan — Reverse-Proxy Path Prefix Support

## Group 1 — Config plumbing

1. Add `JENTIC_ROOT_PATH = os.getenv("JENTIC_ROOT_PATH", "").rstrip("/")` to `src/config.py` next to the existing `JENTIC_PUBLIC_HOSTNAME` block.
2. In `src/config.py`, validate the prefix at import time: if non-empty, must start with `/`, must not contain whitespace, `?`, `#`, or `..`. On invalid value, raise `RuntimeError("JENTIC_ROOT_PATH must start with '/' and contain no whitespace, query, fragment, or '..'")`. Mirrors the existing `AGENT_NONCE_WINDOW <= AGENT_ASSERTION_MAX_AGE` validation pattern.
3. Add a `JENTIC_ROOT_PATH` block to `.env.example` after the `JENTIC_PUBLIC_HOSTNAME` block. Comment must mention: opt-in; pair with `JENTIC_PUBLIC_BASE_URL` when mounting; falls back to `X-Forwarded-Prefix` when unset.
4. Add `JENTIC_ROOT_PATH: ${JENTIC_ROOT_PATH:-}` to `compose.yml` next to the existing `JENTIC_PUBLIC_HOSTNAME` / `JENTIC_PUBLIC_BASE_URL` lines.

## Group 2 — Backend `root_path` wiring

5. Pass `root_path=JENTIC_ROOT_PATH` to the `FastAPI(...)` constructor in `src/main.py` (existing constructor near line 128). Add `JENTIC_ROOT_PATH` to the existing `from src.config import …` import.
6. Add a new ASGI-style middleware class (e.g. `ForwardedPrefixMiddleware`) in `src/main.py` (or extracted into `src/middleware/forwarded_prefix.py` if the plan author prefers a separate module). Implementation: `async def __call__(self, scope, receive, send)`. When `scope["type"] == "http"` and `JENTIC_ROOT_PATH` is empty, read `X-Forwarded-Prefix` from `scope["headers"]`, normalise (single value, strip trailing slash, validate shape), and set `scope["root_path"]` to the normalised value before delegating. Register **after** `negotiate_middleware` so it ends up the outermost middleware (Starlette's reverse-registration order).
7. Update `build_absolute_url` in `src/utils.py:8-26` to prepend `request.scope.get("root_path", "")` to the path argument before concatenation. Preserve all existing `X-Forwarded-Host` / `X-Forwarded-Proto` / `JENTIC_PUBLIC_HOSTNAME` precedence semantics. Verify all existing call sites (`src/main.py:306`, `src/routers/oauth_brokers.py:592, 1163`, any others surfaced by `grep -rn build_absolute_url src/`) continue to behave correctly with the change.

## Group 3 — Backend `index.html` and hand-rolled docs

8. Add a private helper `_render_index(request: Request) -> HTMLResponse` near `STATIC_DIR` in `src/main.py`. Reads `STATIC_DIR / "index.html"` as bytes, substitutes the literal `<base href="/">` with `<base href="{root_path}/">` derived from `request.scope.get("root_path", "")` (note: when `root_path == ""`, the substitution yields `<base href="/">` — same as today). Return `HTMLResponse(body, media_type="text/html")` with appropriate cache headers. Behaviour matches `FileResponse(index_path)` for the unmounted case.
9. Replace `FileResponse(index_path)` in the root handler `@app.get("/")` (`src/main.py:385-390`) with `_render_index(request)`. Update the route signature to accept `request: Request`.
10. Replace `FileResponse(index_path)` in `spa_middleware` (`src/main.py:481-501`, around line 496) with `_render_index(request)`, preserving the existing `Vary: Accept` and `Cache-Control: no-store` response headers.
11. Update the hand-rolled `/docs` Swagger HTML (`src/main.py:397-438`) so `<link href="/static/swagger-ui.css">`, `<script src="/static/swagger-ui-bundle.js">`, and `url: "/openapi.json"` (line 427, inside the JS init) all prepend `request.scope.get("root_path", "")`. Update the `/docs` route signature to accept `request: Request` if it does not already.
12. Update the `/redoc` handler (`src/main.py:442-448`) to compute `openapi_url = f"{root_path}/openapi.json"` and `redoc_js_url = f"{root_path}/static/redoc.standalone.js"` from `request.scope["root_path"]`, then pass both into `get_redoc_html(...)`.

## Group 4 — Frontend

13. Change `base: '/'` to `base: './'` in `ui/vite.config.ts` (around line 54). Verify the dev server still serves correctly with this change.
14. In `ui/src/App.tsx`, read the basename from the DOM at module load:
    ```ts
    const basename = new URL(document.baseURI).pathname.replace(/\/$/, '') || undefined;
    const router = createBrowserRouter([...], { basename });
    ```
    Position the assignment immediately above the existing `createBrowserRouter` call. The `|| undefined` collapses the empty-string case so React Router treats it as no-basename.
15. In `ui/src/main.tsx` (around line 10), replace `OpenAPI.BASE = '';` with `OpenAPI.BASE = document.baseURI.replace(/\/$/, '');`. Before changing, inspect `ui/src/api/generated/core/request.ts` (or equivalent) to confirm the generated client builds absolute paths starting with `/` — if it already concatenates against `OpenAPI.BASE`, this change is correct; if it prepends differently, adjust the assignment accordingly.

## Group 5 — Tests

16. Create `tests/test_root_path.py` with three test scenarios using the parallel-app construction pattern from `tests/test_html_rendering.py:29-46`:

    - **Mode A (unset, regression).** Use the shared `app` fixture from `tests/conftest.py`. Assert: `GET /` returns HTTP 200 with body containing `<base href="/">`; `GET /openapi.json` returns 200 valid JSON; `GET /docs` returns 200 with body containing `swagger-ui-bundle.js`; `GET /health` returns 200; `GET /credentials` (browser `Accept: text/html`) returns 200 SPA shell.
    - **Mode B (env, `JENTIC_ROOT_PATH=/foo`).** Set the env var, then construct a fresh `FastAPI` instance using the parallel-app pattern (or via `monkeypatch.setenv` + module reimport in a session-scoped fixture). Assert: `GET /foo/` returns 200 with `<base href="/foo/">`; `GET /foo/credentials` (browser `Accept`) returns SPA shell with `<base href="/foo/">`; `GET /foo/openapi.json` returns 200 valid JSON; `GET /foo/docs` returns 200 with `swagger-ui-bundle.js`; `GET /foo/health` returns 200.
    - **Mode C (header, `X-Forwarded-Prefix: /foo`).** Use the shared `app` fixture (no env var). Send the header on every request. Assert: `GET /foo/` with the header returns 200 with `<base href="/foo/">`; `GET /foo/credentials` with the header returns SPA shell with `<base href="/foo/">`; `GET /foo/openapi.json` with the header returns 200 valid JSON; `GET /foo/docs` with the header returns 200.
    Include at least one assertion per mode that catches regressions in `build_absolute_url` (e.g. `/health` response body's self-link contains the prefix in Modes B and C).

17. Add a Docker E2E spec under `ui/e2e/docker/` (e.g. `prefix-mount.spec.ts`). Configuration must boot the container with `JENTIC_ROOT_PATH=/foo` (a second container instance separate from the one `ci-docker.yml` already starts at `/`, or via Playwright's `webServer` per-config). The spec navigates to `/foo/`, expects the SPA shell to render, clicks the Credentials nav link, expects URL `/foo/credentials` and the Credentials page to render, reloads the page, and re-asserts the page renders (validating the cold-boot deep-link path through `createBrowserRouter`'s `basename`). One spec; one container start.

## Group 6 — Docs and roadmap lifecycle

18. Add a `JENTIC_ROOT_PATH` row to the `README.md` "Configuration" table. Description: "Path prefix to mount the app under, e.g. `/jentic`. Pair with `JENTIC_PUBLIC_BASE_URL` (which must include the prefix) for OAuth issuer correctness. If unset, falls back to `X-Forwarded-Prefix` per request."
19. Add `JENTIC_ROOT_PATH` to the "Key environment variables" list in `.claude/CLAUDE.md` for agent-context completeness.
20. Add a "Mounting under a path prefix" subsection to `docs/deploy/digitalocean/README.md` after the existing Caddy reverse-proxy snippet, showing a `handle_path /jentic/* { reverse_proxy localhost:8900 }` variant alongside the matching `JENTIC_ROOT_PATH=/jentic` and `JENTIC_PUBLIC_BASE_URL=https://example.com/jentic` env line.
21. Delete the Phase 25 entry from `specs/roadmap.md` (the `## Phase 25 — Reverse-Proxy Path Prefix Support` block + its trailing blank line). Per the lifecycle rule in `specs/roadmap.md`, do NOT renumber surrounding phases — phase numbers are stable identifiers.

## Group 7 — Verify

22. `pdm run lint` exits 0 (ruff check + ruff format --check --diff).
23. `pdm run test -- tests/test_root_path.py -v` exits 0 — the new three-mode tests pass.
24. `pdm run test` exits 0 — full backend suite passes; no regression in `tests/test_health_and_meta.py`, `tests/test_openapi_contract.py`, `tests/test_html_rendering.py`, `tests/test_auth_boundary.py`.
25. `pdm run test -- tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec -v` exits 0 — schema content unchanged (no path/security changes; `root_path` is request-time only).
26. `cd ui && npm run lint` exits 0.
27. `cd ui && npx tsc --noEmit` exits 0.
28. `cd ui && npm run test:run` exits 0 — Vitest browser-mode suite passes (existing tests use `MemoryRouter`; basename behaviour is exercised by the Docker E2E in step 29).
29. `cd ui && npm run test:e2e:docker` exits 0 — including the new prefix-mounted spec.
30. Manual smoke against a built container with `-e JENTIC_ROOT_PATH=/foo`:
    - `curl -sS http://localhost:8900/foo/ | grep -F '<base href="/foo/">'` exits 0
    - `curl -sS http://localhost:8900/foo/credentials | grep -F '<base href="/foo/">'` exits 0
    - `curl -sS http://localhost:8900/foo/openapi.json` returns valid JSON
    - `curl -sS http://localhost:8900/foo/docs | grep -q swagger-ui-bundle.js` exits 0
    - `curl -sS -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/` (without env var, fresh container) returns body containing `<base href="/foo/">`
