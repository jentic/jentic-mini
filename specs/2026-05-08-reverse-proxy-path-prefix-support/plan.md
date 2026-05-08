# Phase 25 Plan — Reverse-Proxy Path Prefix Support

## Group 1 — Config plumbing

1. Add `JENTIC_ROOT_PATH` resolution to `src/config.py` next to the existing `JENTIC_PUBLIC_HOSTNAME` block. Read `os.getenv("JENTIC_ROOT_PATH", "")`; treat `""` and `"/"` as "no mount" (final value `""`). For any other value, strip exactly one trailing `/` if present (`"/foo/"` → `"/foo"`; `"/foo"` → `"/foo"`). Use `value[:-1] if value.endswith("/") and len(value) > 1 else value` rather than `.rstrip("/")` so `"//"` stays as `"//"` and surfaces in step 2's validator instead of silently collapsing.
2. In `src/config.py`, validate the normalised prefix at import time: if non-empty, must start with `/`, must not contain whitespace, `?`, `#`, `..`, or consecutive `//`. On invalid value, raise `RuntimeError("JENTIC_ROOT_PATH must start with '/' and contain no whitespace, query, fragment, '..', or '//'")`. Mirrors the existing `AGENT_NONCE_WINDOW <= AGENT_ASSERTION_MAX_AGE` validation pattern.
3. Add a `JENTIC_ROOT_PATH` block to `.env.example` after the `JENTIC_PUBLIC_HOSTNAME` block. Comment must mention: opt-in; pair with `JENTIC_PUBLIC_BASE_URL` when mounting; falls back to `X-Forwarded-Prefix` when unset.
4. Add `JENTIC_ROOT_PATH: ${JENTIC_ROOT_PATH:-}` to `compose.yml` next to the existing `JENTIC_PUBLIC_HOSTNAME` / `JENTIC_PUBLIC_BASE_URL` lines.

## Group 2 — Backend `root_path` wiring

5. Pass `root_path=JENTIC_ROOT_PATH` to the `FastAPI(...)` constructor in `src/main.py` (existing constructor near line 128). Add `JENTIC_ROOT_PATH` to the existing `from src.config import …` import.
6. Add a new ASGI-style middleware class (e.g. `ForwardedPrefixMiddleware`) in `src/main.py` (or extracted into `src/middleware/forwarded_prefix.py` if the plan author prefers a separate module). Implementation: `async def __call__(self, scope, receive, send)`. When `scope["type"] == "http"` and `JENTIC_ROOT_PATH` is empty, read `X-Forwarded-Prefix` from `scope["headers"]`, normalise (single value, strip trailing slash, validate shape), and set `scope["root_path"]` to the normalised value before delegating. Register **after both `APIKeyMiddleware` and `negotiate_middleware`** so it ends up the outermost middleware in Starlette's reverse-registration order — i.e. it runs first on the way in, mutating `scope["root_path"]` before either of the other two reads `request.url.path`.
7. Update `build_absolute_url` in `src/utils.py:8-26` to prepend `request.scope.get("root_path", "")` to the path argument before concatenation. Preserve all existing `X-Forwarded-Host` / `X-Forwarded-Proto` / `JENTIC_PUBLIC_HOSTNAME` precedence semantics. Verify all existing call sites (`src/main.py:306`, `src/routers/oauth_brokers.py:592, 1163`, any others surfaced by `grep -rn build_absolute_url src/`) continue to behave correctly with the change.

## Group 3 — Backend `index.html` and hand-rolled docs

8. Split the SPA index rendering into a pure transformation and an HTTP wrapper, both in `src/main.py` near `STATIC_DIR`:

    a. Pure helper `_inject_base_href(html: bytes, root_path: str) -> bytes` — when `root_path` is non-empty, replace the literal `b'<base href="/" />'` (the exact form used in `ui/index.html:6`, preserved verbatim by the Vite build into `static/index.html`) with `f'<base href="{root_path}/" />'.encode()`. When `root_path == ""`, return `html` unchanged. Pure function — easily unit-testable with synthetic bytes.

    b. HTTP wrapper `_render_index(request: Request) -> HTMLResponse` — reads `STATIC_DIR / "index.html"` as bytes, calls `_inject_base_href(body, request.scope.get("root_path", ""))`, returns `HTMLResponse(body, media_type="text/html")`.

    Both `_render_index` callsites (root handler and `spa_middleware`) reuse the wrapper; the pure helper is what the tests in step 16 hit primarily.
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
15. In `ui/src/main.tsx` (around line 10), replace `OpenAPI.BASE = '';` with `OpenAPI.BASE = new URL(document.baseURI).pathname.replace(/\/$/, '');`. Verified at spec time: `ui/src/api/generated/core/request.ts:96` builds URLs as `${config.BASE}${path}` where `path` starts with `/` — so setting `OpenAPI.BASE = "/foo"` (extracted from `<base href="/foo/">`) yields `/foo/credentials`, exactly the prefixed absolute path needed. Reading `pathname` (not the full `document.baseURI`) keeps `OpenAPI.BASE` as a path, not an absolute URL — preserves the same-origin assumption.

## Group 5 — Tests

16. **Unit-test the pure transformation.** Add `tests/test_root_path_unit.py` (or a class within `tests/test_root_path.py`) covering `_inject_base_href` with synthetic bytes — no filesystem access, no app fixture:

    - `_inject_base_href(b'<base href="/" />', "")` returns the bytes unchanged.
    - `_inject_base_href(b'<base href="/" />', "/foo")` returns `b'<base href="/foo/" />'`.
    - `_inject_base_href(b'<base href="/" />', "/foo/bar")` returns `b'<base href="/foo/bar/" />'`.
    - HTML without the literal target tag returns unchanged regardless of `root_path` (defensive — substitution is a no-op rather than a corruption).
    - `JENTIC_ROOT_PATH` config validation: parametrize over invalid values (`"foo"`, `"/foo bar"`, `"/foo?q=1"`, `"/foo#frag"`, `"/foo/../bar"`, `"//"`) and assert each raises `RuntimeError`; valid values (`""`, `"/"`, `"/foo"`, `"/foo/"`, `"/foo/bar"`) succeed and produce the expected normalised output.

17. **Add the SPA fixture.** Create `tests/fixtures/index.html` containing the minimum HTML head matching `ui/index.html`'s shape — at minimum `<!doctype html><html><head><base href="/" /></head><body></body></html>`. The full Vite build artifact is gitignored (`static/index.html`), so backend CI doesn't have it; this fixture lets integration tests exercise `_render_index` end-to-end without depending on a UI build step.

18. **Integration tests for the three modes.** Add `tests/test_root_path.py`. Use a session-scoped fixture that monkeypatches `src.main.STATIC_DIR` to `tests/fixtures/` so `_render_index` reads the fixture instead of the real (absent) build artifact. Then:

    - **Mode A (unset, regression).** Use the shared `app` fixture from `tests/conftest.py`. Assert: `GET /` returns HTTP 200 with body containing `<base href="/" />`; `GET /openapi.json` returns 200 valid JSON; `GET /docs` returns 200 with body containing `swagger-ui-bundle.js`; `GET /health` returns 200 with self-link not prefixed; `GET /credentials` (browser `Accept: text/html`) returns 200 SPA shell.
    - **Mode B (env, `JENTIC_ROOT_PATH=/foo`).** Construct a fresh `FastAPI` instance in a module-scoped fixture: set `JENTIC_ROOT_PATH=/foo` via `monkeypatch.setenv` BEFORE importing `src.main`, then `importlib.reload(src.config)` and `importlib.reload(src.main)` to pick up the env. Assert: `GET /foo/` returns 200 with `<base href="/foo/" />`; `GET /foo/credentials` (browser `Accept`) returns SPA shell with `<base href="/foo/" />`; `GET /foo/openapi.json` returns 200 valid JSON; `GET /foo/docs` returns 200 with `swagger-ui-bundle.js`; `GET /foo/health` returns 200 with self-link prefixed by `/foo`.
    - **Mode C (header, `X-Forwarded-Prefix: /foo`).** Use the shared `app` fixture (no env var). Send the header on every request. Assert: `GET /foo/` with the header returns 200 with `<base href="/foo/" />`; `GET /foo/credentials` with the header returns SPA shell with `<base href="/foo/" />`; `GET /foo/openapi.json` with the header returns 200 valid JSON; `GET /foo/docs` with the header returns 200; `GET /foo/health` with the header returns 200 with self-link prefixed by `/foo`.

    Each mode must assert on `build_absolute_url`-derived self-links so a regression in `root_path` propagation through that helper surfaces directly.

19. **Docker E2E spec.** Add `ui/e2e/docker/prefix-mount.spec.ts`. Configuration must boot the container with `JENTIC_ROOT_PATH=/foo` (a second container instance separate from the one `ci-docker.yml` already starts at `/`, or via Playwright's `webServer` per-config). The spec navigates to `/foo/`, expects the SPA shell to render, clicks the Credentials nav link, expects URL `/foo/credentials` and the Credentials page to render, reloads the page, and re-asserts the page renders (validating the cold-boot deep-link path through `createBrowserRouter`'s `basename`). One spec; one container start.

## Group 6 — Docs and roadmap lifecycle

20. Add a `JENTIC_ROOT_PATH` row to the `README.md` "Configuration" table. Description: "Path prefix to mount the app under, e.g. `/jentic`. Pair with `JENTIC_PUBLIC_BASE_URL` (which must include the prefix) for OAuth issuer correctness. If unset, falls back to `X-Forwarded-Prefix` per request."
21. Add `JENTIC_ROOT_PATH` to the "Key environment variables" list in `.claude/CLAUDE.md` for agent-context completeness.
22. Add a "Mounting under a path prefix" subsection to `docs/deploy/digitalocean/README.md` after the existing Caddy reverse-proxy snippet, showing a `handle_path /jentic/* { reverse_proxy localhost:8900 }` variant alongside the matching `JENTIC_ROOT_PATH=/jentic` and `JENTIC_PUBLIC_BASE_URL=https://example.com/jentic` env line.
23. Delete the Phase 25 entry from `specs/roadmap.md` (the `## Phase 25 — Reverse-Proxy Path Prefix Support` block + its trailing blank line). Per the lifecycle rule in `specs/roadmap.md`, do NOT renumber surrounding phases — phase numbers are stable identifiers.

## Group 7 — Verify

24. `pdm run lint` exits 0 (ruff check + ruff format --check --diff).
25. `pdm run test -- tests/test_root_path_unit.py tests/test_root_path.py -v` exits 0 — the unit tests for `_inject_base_href` + config validation, plus the three-mode integration tests, all pass.
26. `pdm run test` exits 0 — full backend suite passes; no regression in `tests/test_health_and_meta.py`, `tests/test_openapi_contract.py`, `tests/test_html_rendering.py`, `tests/test_auth_boundary.py`.
27. `pdm run test -- tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec -v` exits 0 — schema content unchanged (no path/security changes; `root_path` is request-time only).
28. `cd ui && npm run lint` exits 0.
29. `cd ui && npx tsc --noEmit` exits 0.
30. `cd ui && npm run test:run` exits 0 — Vitest browser-mode suite passes (existing tests use `MemoryRouter`; basename behaviour is exercised by the Docker E2E in step 32).
31. `cd ui && npm run test:e2e:docker` exits 0 — including the new prefix-mounted spec.
32. Manual smoke against a built container with `-e JENTIC_ROOT_PATH=/foo`:
    - `curl -sS http://localhost:8900/foo/ | grep -F '<base href="/foo/" />'` exits 0
    - `curl -sS http://localhost:8900/foo/credentials | grep -F '<base href="/foo/" />'` exits 0
    - `curl -sS http://localhost:8900/foo/openapi.json` returns valid JSON
    - `curl -sS http://localhost:8900/foo/docs | grep -q swagger-ui-bundle.js` exits 0
    - `curl -sS -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/` (without env var, fresh container) returns body containing `<base href="/foo/" />`
