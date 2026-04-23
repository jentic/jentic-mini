---
type: constitution
section: tech-stack
generated_by: spec-driven-agent
generated_at: 2026-04-23T00:00:00Z
sources:
  - @pyproject.toml
  - @ui/package.json
  - @Dockerfile
  - @src/main.py
  - @src/db.py
  - @src/bm25.py
  - @docs/ARCHITECTURE.md
  - @docs/ROADMAP.md
  - @.claude/templates/sdd/constitution/tech-stack.example.md
confidence: high
---

# Tech Stack

Jentic Mini uses the following technology choices based on the current repository state and
implementation evidence.

## Architecture Summary

- **Application style:** Client–server hybrid — FastAPI JSON API backend + React SPA admin UI served as static files from the same server
- **Primary language(s):** Python 3.11+ (backend), TypeScript (frontend)
- **Rendering model:** API-only for agents; SPA (React) for human admin; content-negotiated (browser → HTML/SPA, client → JSON)
- **Deployment/runtime shape:** Container (Docker multi-stage build); also runnable from source for development
- **Current maturity:** Early-stage / Early Access (v0.9.0; not recommended for production)

## Core Stack

| Layer | Choice | Evidence / Rationale |
|---|---|---|
| Backend language | Python 3.11+ | `pyproject.toml`: `requires-python = ">=3.11"`; Dockerfile: `python:3.11-slim` |
| HTTP server | FastAPI 0.136 + uvicorn 0.44 (standard extras) | `pyproject.toml` dependencies; `src/main.py` imports |
| Frontend language | TypeScript 5.9 | `ui/package.json` devDependencies; `ui/tsconfig.json` present |
| Frontend framework | React 18 | `ui/package.json` dependencies |
| Frontend build | Vite 7 | `ui/package.json`; `ui/vite.config.ts` present |
| UI styling | TailwindCSS 4 (via `@tailwindcss/vite` plugin) | `ui/package.json` devDependencies; docs/ROADMAP.md confirms v0.3 upgrade |
| Python packaging | PDM 2.25.5 | Dockerfile `RUN curl .../install-pdm.py`; `pdm.lock` present |
| Container | Docker multi-stage (Node 24 UI build → Python 3.11-slim runtime) | `Dockerfile` |

## Key Libraries and Frameworks

**Backend:**
- **fastapi** — async HTTP API framework; all routes, middleware, and OpenAPI schema defined here
- **uvicorn[standard]** — ASGI server with hot reload in dev mode
- **aiosqlite** — async SQLite driver for database access
- **alembic** — schema migration management (`alembic/versions/`)
- **rank-bm25** — in-memory BM25 full-text search index over registered operations and workflows (rebuilt at startup and after imports)
- **arazzo-runner** — Python library for executing Arazzo multi-step workflow specs
- **jentic-openapi-common** — shared OpenAPI utilities from the Jentic ecosystem
- **cryptography (Fernet)** — symmetric encryption for credential vault (write-only semantics; values never returned after creation)
- **python-jose[cryptography]** — JWT generation and validation for human admin sessions (30-day TTL, auto-refresh)
- **bcrypt** — password hashing for human admin accounts
- **httpx** — async HTTP client used for upstream version checks and self-registration
- **aiohttp** — async HTTP client used within `arazzo-runner` workflow steps
- **pyyaml** — YAML parsing for OpenAPI and Arazzo specs

**Frontend:**
- **@tanstack/react-query 5** — server state management and data fetching
- **react-router-dom 6** — client-side routing for the SPA
- **@jentic/arazzo-ui** — workflow visualization component (diagram/docs/split views); from [jentic-arazzo-tools](https://github.com/jentic/jentic-arazzo-tools)
- **lucide-react** — SVG icon library
- **clsx + tailwind-merge** — conditional class composition (`cn()` utility)
- **msw 2** — API mocking in tests (Service Worker-based)

## Data and Storage

- **Primary storage:** SQLite at `/app/data/jentic-mini.db` (inside container); persisted via Docker volume
- **Access pattern:** Raw SQL via `aiosqlite` (no ORM); query building is manual in `src/db.py`
- **Migrations:** Alembic (`alembic/versions/`); migrations run automatically at container startup via `run_migrations()` in `main.py` lifespan
- **Caching / state:** BM25 index is in-memory; catalog manifest from GitHub is cached on disk for 24 hours; version check is in-memory with 6-hour TTL
- **Credential vault:** Fernet-encrypted values stored in the `credentials` table; the vault key (`JENTIC_VAULT_KEY`) is auto-generated at first run and persisted to `/app/data/vault.key`
- **Spec/workflow storage:** OpenAPI spec files and Arazzo workflow files stored on disk under `/app/data/specs/` and `/app/data/workflows/`

## Testing

- **Backend test framework:** pytest + pytest-asyncio (`pyproject.toml` dev dependencies)
- **Backend test types:** Integration tests against the FastAPI app (via `httpx.AsyncClient`); contract tests via schemathesis; credential, policy, auth, and broker tests
- **Frontend test framework:** Vitest 4 (browser mode, Chromium via Playwright)
- **Frontend test types:** Unit + integration tests (Vitest + `@testing-library/react` + MSW), E2E tests (Playwright), accessibility checks (axe-core)
- **Current testing pattern:** Backend has integration/contract test suite but no unit tests for individual modules yet (noted as a gap in ROADMAP.md). Frontend has 143+ integration tests and 35 E2E specs as of v0.5.

## Tooling and Developer Experience

- **Local development:** `docker compose -f compose.yml -f compose.dev.yml up` starts backend with hot reload (Python source volume-mounted) and a Vite dev server on port 5173 with HMR. Alternatively, Vite can run directly on the host with `cd ui && npm run dev`.
- **Build / release:** `cd ui && npm run build` produces the static bundle; `docker compose up -d --build` rebuilds the full image. Production releases use `semantic-release` for git tags + GitHub Releases + Docker publish CI.
- **Formatting / linting (Python):** `ruff` (check + format); configured in `pyproject.toml`; PDM scripts `lint` and `lint:fix`
- **Formatting / linting (TypeScript):** ESLint 9 + prettier 3; `lint-staged` runs on commit via husky
- **Type checking:** TypeScript strict mode (frontend); Python has no static type checking configured (no mypy in dev deps)
- **CI/CD:** GitHub Actions — `ci-ui.yml` (path-filtered, TypeScript check + Vitest + Playwright) and `ci-docker.yml` (always runs, Docker layer caching); Dependabot for dep updates

## Deployment and Operations

- **Deployment target:** Docker container; published to DockerHub (`jentic/jentic-mini`) and GHCR (`ghcr.io/jentic/jentic-mini`); compatible with `amd64` and `arm64`
- **Port:** 8900 (exposed in Dockerfile; configurable via compose)
- **Environment management:** Optional `.env` file or Docker env vars; key vars: `JENTIC_VAULT_KEY`, `JENTIC_PUBLIC_HOSTNAME`, `LOG_LEVEL`, `JENTIC_TELEMETRY`, `JENTIC_UID`/`JENTIC_GID`
- **Observability:** Python stdlib `logging` (configurable with `LOG_LEVEL`); execution traces stored in SQLite and queryable via `GET /traces`; `GET /version` version-check endpoint; anonymous install telemetry (opt-out via `JENTIC_TELEMETRY=off`)
- **Error handling:** FastAPI exception handlers; broker propagates upstream HTTP status and `failed_step` detail on workflow errors; no rate limiting or audit trail currently

## Constraints and Conventions

- **Broker routing constraint:** The broker identifies upstream hosts by requiring the first path segment to contain a `.` (dot). This means `localhost`, bare hostnames, and raw IPs are not routable through the broker — only public domain-style hostnames work (e.g. `api.stripe.com`). This is a known gap.
- **Route registration order:** The broker catch-all route (`/{target:path}`) must be registered last in `main.py`; all internal routers take priority by registration order. Violating this causes silent failures where internal endpoints become unreachable.
- **Credential write-only semantics:** Credential values are encrypted on write and never returned via the API. The vault key must be persisted; losing it means losing access to all stored credentials.
- **Non-root container:** The container runs as the `jentic` system user (UID configurable via `JENTIC_UID`/`JENTIC_GID`).
- **Content negotiation:** SPA routes return `index.html` for browser requests (`Accept: text/html`), and JSON for API clients. This is implemented as an HTTP middleware in `main.py`.
- **Python target version:** Python 3.11 minimum (ruff `target-version = "py311"`); the runtime image is also Python 3.11-slim.
- **UI ESLint guardrails:** `no-restricted-syntax` rules in `src/pages/` enforce use of the owned UI component library (no raw `<button>`, `<input>`, etc. in page code).

## What We Are Not Using

- No **ORM** (SQLAlchemy, Tortoise, etc.) — raw `aiosqlite` SQL throughout `src/db.py`
- No **Redis or external cache** — all caching is in-memory or on-disk SQLite/file
- No **TypeScript strict null checks enforced in all files** — ~166 `any`/`@ts-ignore` instances noted as a known debt in ROADMAP.md (v0.6 context)
- No **mypy or pyright** for Python type checking — not present in `pyproject.toml` dev dependencies
- No **CDN dependency** — Swagger UI, Redoc, and other assets are vendored locally in `static/`

## Open Questions / Uncertain Areas

- Python `arazzo-runner` (PyPI) is listed as a high-priority migration target to the TypeScript implementation from `jentic-arazzo-tools`; the current Python runner is an interim choice
- No rate limiting is in place on any endpoint (including login and broker); this is explicitly noted as a pre-production requirement in ROADMAP.md
- The `api_keys` table in the DB schema is described as "reserved for future fine-grained scope assignment" — its eventual design is not yet determined

