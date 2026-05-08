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
8. **Scope auth cookies to the mount.** Update every `set_cookie` and `delete_cookie` call to pass `path=request.scope.get("root_path") or "/"`. Specifically: `src/auth.py:315`, `src/routers/user.py:112,209,214`, and the corresponding `delete_cookie` at `src/routers/user.py:300`. Starlette's `set_cookie` defaults `path="/"`, so without this change a `/foo`-mounted instance issues cookies valid for the whole origin — under shared-tenant deploys (`example.com/jentic` next to `example.com/other-app`) the session cookie leaks to siblings. Reading `path` from `scope["root_path"]` (rather than the static `JENTIC_ROOT_PATH` config) keeps Mode C correct: when the prefix arrives via `X-Forwarded-Prefix`, the new ASGI middleware has already set `scope["root_path"]` by the time the route handler issues the cookie.

## Group 3 — Backend `index.html` and hand-rolled docs

9. Split the SPA index rendering into a pure transformation and an HTTP wrapper, both in `src/main.py` near `STATIC_DIR`:

    a. Pure helper `_inject_base_href(html: bytes, root_path: str) -> bytes` — when `root_path` is non-empty, substitute the existing `<base ...>` tag using a tolerant regex (e.g. `re.compile(rb'<base\s+href="[^"]*"\s*/?\s*>')`) with `f'<base href="{root_path}/" />'.encode()`. Use `count=1` so we only touch the first occurrence. The regex absorbs formatting drift across Vite versions: with-or-without-self-close, with-or-without-spaces. When `root_path == ""`, return `html` unchanged. Pure function — easily unit-testable with synthetic bytes; covered in step 18.

    b. HTTP wrapper `_render_index(request: Request) -> HTMLResponse` — reads `STATIC_DIR / "index.html"` as bytes, calls `_inject_base_href(body, request.scope.get("root_path", ""))`, returns `HTMLResponse(body, media_type="text/html")`.

    Both `_render_index` callsites (root handler and `spa_middleware`) reuse the wrapper; the pure helper is what the tests in step 18 hit primarily.
10. Replace `FileResponse(index_path)` in the root handler `@app.get("/")` (`src/main.py:385-390`) with `_render_index(request)`. Update the route signature to accept `request: Request`.
11. Update `spa_middleware` (`src/main.py:481-501`) to (a) strip `root_path` from `path` before matching `_SPA_PATHS`, and (b) replace `FileResponse(index_path)` with `_render_index(request)` while preserving the existing `Vary: Accept` and `Cache-Control: no-store` response headers. The path-strip is required because `_SPA_PATHS` is hardcoded against unprefixed routes (`/credentials`, `/toolkits`, etc.) but `request.url.path` returns the full path including the mount prefix — so `/foo/credentials` won't match `/credentials` without explicit stripping. Concretely: `path = request.url.path; root_path = request.scope.get("root_path", ""); if root_path and path.startswith(root_path): path = path[len(root_path):] or "/"`. Apply the same strip before the `is_spa_excluded` regex check so the OAuth `connect-callback` exclusion still fires under prefix.
12. Update the hand-rolled `/docs` Swagger HTML (`src/main.py:397-438`) so `<link href="/static/swagger-ui.css">`, `<script src="/static/swagger-ui-bundle.js">`, and `url: "/openapi.json"` (line 427, inside the JS init) all prepend `request.scope.get("root_path", "")`. Update the `/docs` route signature to accept `request: Request` if it does not already.
13. Update the `/redoc` handler (`src/main.py:442-448`) to compute `openapi_url = f"{root_path}/openapi.json"` and `redoc_js_url = f"{root_path}/static/redoc.standalone.js"` from `request.scope["root_path"]`, then pass both into `get_redoc_html(...)`.

## Group 4 — Frontend

14. Change `base: '/'` to `base: './'` in `ui/vite.config.ts` (around line 54). Verify the dev server still serves correctly with this change.
15. In `ui/src/App.tsx`, read the basename from the DOM at module load:
    ```ts
    const basename = new URL(document.baseURI).pathname.replace(/\/$/, '') || undefined;
    const router = createBrowserRouter([...], { basename });
    ```
    Position the assignment immediately above the existing `createBrowserRouter` call. The `|| undefined` collapses the empty-string case so React Router treats it as no-basename.
16. In `ui/src/main.tsx` (around line 10), replace `OpenAPI.BASE = '';` with `OpenAPI.BASE = new URL(document.baseURI).pathname.replace(/\/$/, '');`. Verified at spec time: `ui/src/api/generated/core/request.ts:96` builds URLs as `${config.BASE}${path}` where `path` starts with `/` — so setting `OpenAPI.BASE = "/foo"` (extracted from `<base href="/foo/">`) yields `/foo/credentials`, exactly the prefixed absolute path needed. Reading `pathname` (not the full `document.baseURI`) keeps `OpenAPI.BASE` as a path, not an absolute URL — preserves the same-origin assumption.

## Group 5 — Tests

17. **Unit-test the pure transformation.** Add `tests/test_root_path_unit.py` (or a class within `tests/test_root_path.py`) covering `_inject_base_href` with synthetic bytes — no filesystem access, no app fixture:

    - `_inject_base_href(b'<base href="/" />', "")` returns the bytes unchanged.
    - `_inject_base_href(b'<base href="/" />', "/foo")` returns `b'<base href="/foo/" />'`.
    - `_inject_base_href(b'<base href="/" />', "/foo/bar")` returns `b'<base href="/foo/bar/" />'`.
    - **Formatting-drift coverage** (regex-robustness): inputs `b'<base href="/">'`, `b'<base href="/"/>'`, `b'<base href="/" >'`, `b'<base  href="/"  />'` (extra whitespace) all substitute correctly when `root_path="/foo"` is given — output's `<base href="/foo/" />` regardless of input formatting.
    - HTML without any `<base>` tag returns unchanged regardless of `root_path` (defensive — substitution is a no-op rather than a corruption).
    - `JENTIC_ROOT_PATH` config validation: parametrize over invalid values (`"foo"`, `"/foo bar"`, `"/foo?q=1"`, `"/foo#frag"`, `"/foo/../bar"`, `"//"`) and assert each raises `RuntimeError`; valid values (`""`, `"/"`, `"/foo"`, `"/foo/"`, `"/foo/bar"`) succeed and produce the expected normalised output.

18. **Add the SPA fixture.** Create `tests/fixtures/index.html` containing the minimum HTML head matching `ui/index.html`'s shape — at minimum `<!doctype html><html><head><base href="/" /></head><body></body></html>`. The full Vite build artifact is gitignored (`static/index.html`), so backend CI doesn't have it; this fixture lets integration tests exercise `_render_index` end-to-end without depending on a UI build step.

19. **Integration tests for the three modes.** Add `tests/test_root_path.py`. Use a session-scoped fixture that monkeypatches `src.main.STATIC_DIR` to `tests/fixtures/` so `_render_index` reads the fixture instead of the real (absent) build artifact. Use tolerant attribute-only assertions (`assert b'href="/foo/"' in body`) rather than full-tag matches, so formatting drift in the fixture doesn't cause false failures. Then:

    - **Mode A (unset, regression).** Use the shared `app` fixture from `tests/conftest.py`. Assert: `GET /` returns HTTP 200 with body containing `href="/"` inside a `<base>` tag; `GET /openapi.json` returns 200 valid JSON; `GET /docs` returns 200 with body containing `swagger-ui-bundle.js`; `GET /health` returns 200 with self-link not prefixed; `GET /credentials` (browser `Accept: text/html`) returns 200 SPA shell; `Set-Cookie` on `POST /user/login` carries `Path=/`.
    - **Mode B (env, `JENTIC_ROOT_PATH=/foo`).** Construct a fresh `FastAPI` instance in a module-scoped fixture: set `JENTIC_ROOT_PATH=/foo` via `monkeypatch.setenv` BEFORE importing `src.main`, then `importlib.reload(src.config)` and `importlib.reload(src.main)` to pick up the env. Assert: `GET /foo/` returns 200 with body containing `href="/foo/"`; `GET /foo/credentials` (browser `Accept`) returns SPA shell with `href="/foo/"` (proves both the SPA-fallback path-strip from step 11 AND `<base>` injection from step 9); `GET /foo/openapi.json` returns 200 valid JSON; `GET /foo/docs` returns 200 with body containing `/foo/static/swagger-ui-bundle.js` (proves step 12); `GET /foo/health` returns 200 with self-link prefixed by `/foo`; `Set-Cookie` on login carries `Path=/foo`.
    - **Mode C (header, `X-Forwarded-Prefix: /foo`).** Use the shared `app` fixture (no env var). Send the header on every request. Assert all the same shapes as Mode B; in addition, `Set-Cookie` on login carries `Path=/foo` (proves the cookie path is read from `scope["root_path"]` rather than the static config).

    Each mode must assert on `build_absolute_url`-derived self-links so a regression in `root_path` propagation through that helper surfaces directly.

20. **Docker E2E spec.** Add `ui/e2e/docker/prefix-mount.spec.ts`. Configuration must boot the container with `JENTIC_ROOT_PATH=/foo` (a second container instance separate from the one `ci-docker.yml` already starts at `/`, or via Playwright's `webServer` per-config). The spec navigates to `/foo/`, expects the SPA shell to render, clicks the Credentials nav link, expects URL `/foo/credentials` and the Credentials page to render, reloads the page, and re-asserts the page renders (validating the cold-boot deep-link path through `createBrowserRouter`'s `basename`). One spec; one container start.

## Group 6 — Docs and roadmap lifecycle

21. Add a `JENTIC_ROOT_PATH` row to the `README.md` "Configuration" table. Description: "Path prefix to mount the app under, e.g. `/jentic`. Pair with `JENTIC_PUBLIC_BASE_URL` (which must include the prefix) for OAuth issuer correctness. If unset, falls back to `X-Forwarded-Prefix` per request."
22. Add `JENTIC_ROOT_PATH` to the "Key environment variables" list in `.claude/CLAUDE.md` for agent-context completeness.
23. Add a "Mounting under a path prefix" subsection to `docs/deploy/digitalocean/README.md` after the existing Caddy reverse-proxy snippet, showing a `handle_path /jentic/* { reverse_proxy localhost:8900 }` variant alongside the matching `JENTIC_ROOT_PATH=/jentic` and `JENTIC_PUBLIC_BASE_URL=https://example.com/jentic` env line.
24. Delete the Phase 25 entry from `specs/roadmap.md` (the `## Phase 25 — Reverse-Proxy Path Prefix Support` block + its trailing blank line). Per the lifecycle rule in `specs/roadmap.md`, do NOT renumber surrounding phases — phase numbers are stable identifiers.

## Group 7 — Verify

25. `pdm run lint` exits 0 (ruff check + ruff format --check --diff).
26. `pdm run test -- tests/test_root_path_unit.py tests/test_root_path.py -v` exits 0 — the unit tests for `_inject_base_href` + config validation, plus the three-mode integration tests, all pass.
27. `pdm run test` exits 0 — full backend suite passes; no regression in `tests/test_health_and_meta.py`, `tests/test_openapi_contract.py`, `tests/test_html_rendering.py`, `tests/test_auth_boundary.py`.
28. `pdm run test -- tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec -v` exits 0 — schema content unchanged (no path/security changes; `root_path` is request-time only).
29. `cd ui && npm run lint` exits 0.
30. `cd ui && npx tsc --noEmit` exits 0.
31. `cd ui && npm run test:run` exits 0 — Vitest browser-mode suite passes (existing tests use `MemoryRouter`; basename behaviour is exercised by the Docker E2E in step 33).
32. `cd ui && npm run test:e2e:docker` exits 0 — including the new prefix-mounted spec.
33. Manual smoke against a built container with `-e JENTIC_ROOT_PATH=/foo`:
    - `curl -sS http://localhost:8900/foo/ | grep -F 'href="/foo/"'` exits 0
    - `curl -sS -H 'Accept: text/html' http://localhost:8900/foo/credentials | grep -F 'href="/foo/"'` exits 0
    - `curl -sS http://localhost:8900/foo/openapi.json` returns valid JSON
    - `curl -sS http://localhost:8900/foo/docs | grep -q 'swagger-ui-bundle.js'` exits 0
    - `curl -sS -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/` (without env var, fresh container) returns body containing `href="/foo/"`
    - `curl -sS -i -X POST -H 'Content-Type: application/json' -d '{"username":"…","password":"…"}' http://localhost:8900/foo/user/login | grep -E '^Set-Cookie:.*Path=/foo'` exits 0 (cookie scoped to the mount)
