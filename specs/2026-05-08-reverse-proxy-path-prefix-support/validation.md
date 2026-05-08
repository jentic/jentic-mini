# Phase 25 Validation — Reverse-Proxy Path Prefix Support

## Definition of Done

All of the following must be true before this branch is merged.

### 1. Backend lint clean

```
pdm run lint
```

Exit code 0 (ruff check + ruff format --check --diff per `pyproject.toml`).

### 2. New three-mode backend tests pass

```
pdm run test -- tests/test_root_path.py -v
```

Exit code 0. The file must include all three scenarios — Mode A (unset; regression), Mode B (`JENTIC_ROOT_PATH=/foo`), Mode C (`X-Forwarded-Prefix: /foo` header). Each mode asserts the served HTML's `<base href>` value, the reachability of `/openapi.json`, `/docs`, `/health`, and at least one SPA-fallback route.

### 3. Full backend suite passes (regression gate)

```
pdm run test
```

Exit code 0. Must include passing runs of `tests/test_health_and_meta.py`, `tests/test_openapi_contract.py`, `tests/test_html_rendering.py`, `tests/test_auth_boundary.py` — Phase 25 must not regress any existing-mode test.

### 4. OpenAPI schema content unchanged

```
pdm run test -- tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec -v
```

Exit code 0. `root_path` is a request-time prefix and does not alter schema content (paths, schemas, security). This gate confirms the assumption.

### 5. UI lint clean

```
cd ui && npm run lint
```

Exit code 0.

### 6. UI typecheck clean

```
cd ui && npx tsc --noEmit
```

Exit code 0. Catches errors from the `App.tsx` `basename` and `main.tsx` `OpenAPI.BASE` edits.

### 7. UI Vitest suite passes

```
cd ui && npm run test:run
```

Exit code 0. Existing Vitest tests use `MemoryRouter` (per `ui/src/__tests__/test-utils.tsx`) — they don't exercise `createBrowserRouter`'s `basename`, but they must remain green after the `OpenAPI.BASE` change. Real `basename` coverage is in step 8.

### 8. Docker E2E with prefix mount passes

```
cd ui && npm run test:e2e:docker
```

Exit code 0. Must include the new `ui/e2e/docker/prefix-mount.spec.ts` (or equivalent) that boots the container with `JENTIC_ROOT_PATH=/foo`, navigates to `/foo/`, clicks the Credentials nav link, expects URL `/foo/credentials` and a rendered page, then reloads and re-asserts the page renders. This is the only test layer that exercises a real `createBrowserRouter` against a backend-rendered `<base href="/foo/">`.

### 9. Mode A curl smoke (regression — unset)

Run a built container with no `JENTIC_ROOT_PATH` and no `X-Forwarded-Prefix`. Then:

```
curl -sS http://localhost:8900/ | grep -F '<base href="/">'
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8900/openapi.json
curl -sS http://localhost:8900/docs | grep -q 'swagger-ui-bundle.js'
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8900/health
```

In order: exit 0 with the substring matched; `200`; exit 0; `200`.

### 10. Mode B curl smoke (env-driven)

Run a built container with `-e JENTIC_ROOT_PATH=/foo`. Then:

```
curl -sS http://localhost:8900/foo/ | grep -F '<base href="/foo/">'
curl -sS -H 'Accept: text/html' http://localhost:8900/foo/credentials | grep -F '<base href="/foo/">'
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8900/foo/openapi.json
curl -sS http://localhost:8900/foo/docs | grep -q 'swagger-ui-bundle.js'
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8900/foo/health
```

In order: exit 0; exit 0 (proves SPA fallback fires under prefix); `200`; exit 0; `200`. The `swagger-ui-bundle.js` substring proves the hand-rolled `/docs` HTML was prefix-rewritten — the asset URL must include `/foo/static/...` for the page to actually load Swagger.

### 11. Mode C curl smoke (header-driven)

Run a built container with no `JENTIC_ROOT_PATH`. Then:

```
curl -sS -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/ | grep -F '<base href="/foo/">'
curl -sS -H 'Accept: text/html' -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/credentials | grep -F '<base href="/foo/">'
curl -sS -o /dev/null -w '%{http_code}\n' -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/openapi.json
curl -sS -H 'X-Forwarded-Prefix: /foo' http://localhost:8900/foo/docs | grep -q 'swagger-ui-bundle.js'
```

In order: exit 0; exit 0; `200`; exit 0.

### 12. README.md Configuration section lists `JENTIC_ROOT_PATH`

`README.md` must contain a row or entry naming `JENTIC_ROOT_PATH` with a description that calls out (a) the path-prefix purpose, (b) the `JENTIC_PUBLIC_BASE_URL` pairing requirement, and (c) the `X-Forwarded-Prefix` header fallback.

### 13. `.claude/CLAUDE.md` "Key environment variables" lists `JENTIC_ROOT_PATH`

`.claude/CLAUDE.md` must include a bullet for `JENTIC_ROOT_PATH` in the "Key environment variables" section so future agent context loads see it.

### 14. `specs/roadmap.md` no longer contains the Phase 25 entry

```
grep -nE '^## Phase 25 — Reverse-Proxy Path Prefix Support' specs/roadmap.md
```

Returns no matches. Surrounding phases (24, 26+ if any) remain renumbered exactly as they are today; per `specs/roadmap.md` lifecycle rule the gap at 25 is preserved.

## Not Required

- **Real reverse-proxy round-trip in CI.** No nginx / Caddy / Traefik instance is started. Mode C is exercised by sending `X-Forwarded-Prefix` directly to uvicorn — that is sufficient to validate the middleware behaviour. Wiring a real proxy would test the proxy, not Mini.
- **Schemathesis CLI gate.** `schemathesis` is in dev deps but not wired into CI; `tests/test_openapi_contract.py:55` documents the FastAPI-TestClient incompatibility. Phase 25 does not change schema content — the existing `test_ui_openapi_matches_served_spec` gate (step 4) is the contract enforcement that exists today.
- **Mocked Playwright suite (`npm run test:e2e`) coverage of prefix behaviour.** That suite runs against `http://localhost:5173` (Vite dev), not against the production-built `<base href>` injection. Adding prefix coverage there is not feasible. Step 8's Docker E2E covers it.
- **Pipedream OAuth `connect-callback` URL prefix coverage.** The redirect URL is configured per-broker in the Pipedream dashboard, not derived dynamically from `request.scope["root_path"]`. This is a deployment-configuration concern, not a code concern.
- **WebSocket / streaming endpoints under prefix.** No WebSockets exist; broker streaming is Phase 23.
- **Generated TypeScript client regeneration.** Phase 25 does not change the OpenAPI schema (no path or security changes); `ui/openapi.json` and `ui/src/api/generated/` do not need regenerating. Step 4 confirms.
- **`docs/reverse-proxy.md` as a new file.** README + env-var entry covers the documentation requirement; a dedicated guide is out of scope.
- **`JENTIC_PUBLIC_BASE_URL` auto-derivation.** Operators must set both env vars when mounting; the OAuth-issuer pin is not extended in this phase.
- **Multi-mount validation.** A single `JENTIC_ROOT_PATH` value is supported; serving the same instance at `/foo` and `/bar` simultaneously is out of scope.
