---
type: constitution
section: tech-stack
generated_by: spec-driven-agent
generated_at: 2026-04-23T00:00:00Z
confidence: high
---

# Tech Stack

Jentic Mini uses the following technology choices based on the current repository state and
implementation evidence.

## Architecture Summary

- **Application style:** Client–server hybrid — FastAPI JSON API backend + React SPA admin UI served as static files from the same server
- **Primary language(s):** Python 3.11+ (backend), TypeScript (frontend)
- **Rendering model:** API-only for agents; SPA (React) for human admin; content-negotiated (browser → HTML/SPA, client → JSON, also YAML/Markdown on request)
- **Deployment/runtime shape:** Container (Docker multi-stage build); also runnable from source for development
- **Current maturity:** Early-stage / Early Access (v0.9.0; not recommended for production)

## Core Stack

Load-bearing choices only. Exact versions are tracked in `pyproject.toml`, `ui/package.json`,
and `Dockerfile`.

| Layer | Choice |
|---|---|
| Backend language | Python 3.11+ |
| HTTP server | FastAPI + uvicorn |
| Frontend language | TypeScript (strict) |
| Frontend framework | React |
| Frontend build | Vite |
| UI styling | TailwindCSS 4 (via `@tailwindcss/vite` plugin — no PostCSS, no JS config) |
| Python packaging | PDM |
| Container | Docker multi-stage (Node UI build → Python slim runtime) |
| Compose layout | `compose.yml` (base), `compose.dev.yml` (Vite dev server), `compose.ci.yml` (CI overrides) |

## Architecturally Load-Bearing Libraries

These shape the system — swapping any of them would force architectural change.
Swappable implementation-detail libraries (HTTP clients, password-hash impls, JWT impls,
icon libs, class-merge helpers, YAML parsers, etc.) are not listed here.

**Backend:**
- **FastAPI + uvicorn** — the entire HTTP surface, middleware, and OpenAPI schema
- **aiosqlite + Alembic** — storage and migration model (no ORM)
- **rank-bm25** — in-memory BM25 index for operation and workflow search
- **arazzo-runner** — Arazzo multi-step workflow execution (interim Python engine; TypeScript replacement planned — see roadmap)
- **cryptography (Fernet)** — credential vault encryption contract

**Frontend:**
- **@tanstack/react-query** — server-state management shape (cache, retry, invalidation)
- **react-router-dom** — client routing (routes hand-registered in `ui/src/App.tsx` via `createBrowserRouter`)
- **msw** — fetch-layer mocking; tests mock at the network boundary, not at hooks

**Testing:**
- **pytest + pytest-asyncio** — backend
- **Vitest (browser mode) + Playwright + axe-core** — frontend unit/integration, E2E, and a11y

## Backend Layout

Core modules live in `src/` and routers in `src/routers/`; see `CLAUDE.md` and
`docs/ARCHITECTURE.md` for the current catalog. Load-bearing invariants:

- **Router registration order:** all internal routers are registered first; the broker catch-all (`/{target:path}`) is registered last in `src/main.py`.
- **Content-negotiation middleware** (`src/negotiate.py`) transforms JSON responses into YAML or Markdown based on `Accept`.
- **OAuth brokers** live in `src/brokers/`. Pipedream is the only first-class implementation today and is documented as a temporary bridge; a native `JenticOAuthBroker` is planned as a drop-in replacement per `docs/oauth-broker.md`.

## Data and Storage

- **Primary storage:** SQLite at `/app/data/jentic-mini.db` inside the container; persisted via Docker volume
- **Access pattern:** Raw SQL via `aiosqlite` (no ORM); query building is manual in `src/db.py`
- **Migrations:** Alembic is the schema source of truth; migration files live in `alembic/versions/` and run automatically at container startup via `run_migrations()` in `main.py` lifespan. `docs/ARCHITECTURE.md` is the conceptual data-model reference.
- **Caching / state:** BM25 index is in-memory; catalog manifest from GitHub is cached on disk for 24 hours; version check is in-memory with 6-hour TTL
- **Credential vault:** Fernet-encrypted values in the `credentials` table; the vault key (`JENTIC_VAULT_KEY`) is auto-generated at first run and persisted to `/app/data/vault.key`
- **Spec/workflow storage:** OpenAPI spec files and Arazzo workflow files stored on disk under `/app/data/specs/` and `/app/data/workflows/`

## Testing

- **Backend framework:** pytest + pytest-asyncio (`pyproject.toml` dev deps); schemathesis for OpenAPI contract testing
- **Backend style:** Integration-level against the FastAPI app with a real temp SQLite and real Alembic migrations — no mocking. Tests organized by trust boundary (auth, policy, vault, broker, toolkit, workflow). Module-level unit tests are a known gap.
- **Backend test isolation:** `conftest.py` must set `DB_PATH` **before** any `src.*` import (documented via ruff per-file-ignores for E402/PLC0415). A `_test_lifespan()` fixture skips BM25 rebuild, self-registration, catalog refresh, and OAuth broker loading.
- **Frontend framework:** Vitest 4 in browser mode (Playwright/Chromium), `@testing-library/react`, `msw` for fetch-layer mocking, `axe-core` for accessibility.
- **Frontend style:** Fresh `QueryClient` per test (`retry: false`, `gcTime: 0`), reset MSW handlers between tests, mock at the fetch layer — never mock hooks. Details in `ui/TESTING.md`.
- **E2E:** Playwright with two configs — `playwright.config.ts` (mocked-server + Vite) and `playwright.docker.config.ts` (real-server Docker E2E with `setup` + dependency workflow).

## Tooling and Developer Experience

- **Local development:** `docker compose -f compose.yml -f compose.dev.yml up` starts the backend with hot reload (Python source volume-mounted) and a Vite dev server on port 5173 with HMR. Alternatively, Vite can run on the host with `cd ui && npm run dev`.
- **Build / release:** `cd ui && npm run build` produces the static bundle into `static/` at the project root (gitignored). `docker compose up -d --build` rebuilds the full image. Releases use `semantic-release` for git tags + GitHub Releases + Docker publish CI.
- **Formatting / linting (Python):** `ruff` (check + format) configured in `pyproject.toml` with `target-version = "py311"`. PDM scripts: `lint`, `lint:fix`.
- **Formatting / linting (TypeScript):** ESLint 9 (flat config) + Prettier 3; lint-staged via husky on pre-commit.
- **Type checking:** TypeScript strict mode (frontend); Python has no static type checking configured (no mypy or pyright in dev deps).
- **CI/CD:** GitHub Actions in `.github/workflows/` cover backend, UI, Docker image build, Docker security scanning, CodeQL, `semantic-release`, and Dependabot automation. CI per area is path-filtered.

## Deployment and Operations

- **Deployment target:** Docker container; published to DockerHub (`jentic/jentic-mini`) and GHCR (`ghcr.io/jentic/jentic-mini`); multi-arch (`amd64`, `arm64`)
- **Port:** 8900 (exposed in Dockerfile; configurable via compose)
- **User:** Non-root `jentic` system user; UID/GID configurable via `JENTIC_UID` / `JENTIC_GID`
- **Environment management:** Optional `.env` file or Docker env vars. Key vars: `JENTIC_VAULT_KEY`, `JENTIC_PUBLIC_HOSTNAME`, `JENTIC_TRUSTED_SUBNETS`, `LOG_LEVEL`, `JENTIC_TELEMETRY`, `JENTIC_UID`, `JENTIC_GID`, `DB_PATH`
- **Observability:** Python stdlib `logging` (configurable with `LOG_LEVEL`); execution traces stored in SQLite and queryable via `GET /traces`; `GET /version` (6-hour cache; see `docs/versioning.md`); anonymous install telemetry (opt-out via `JENTIC_TELEMETRY=off`)
- **Error handling:** FastAPI exception handlers; broker propagates upstream HTTP status and `failed_step` detail on workflow errors; no rate limiting or audit trail currently

## Constraints and Conventions

- **Broker routing constraint:** The broker identifies upstream hosts by requiring the first path segment to contain a `.` (dot). `localhost`, bare hostnames, and raw IPs are not routable through the broker today — only public domain-style hostnames (e.g. `api.stripe.com`). This is a known gap addressed in roadmap Phase 1.
- **Route registration order:** The broker catch-all (`/{target:path}`) must be registered last in `main.py`. Violating this silently swallows internal routes (symptom: `No API found for host '…'` on an internal endpoint).
- **Credential write-only semantics:** Credential values are encrypted on write and never returned via the API. The vault key must be persisted — losing it means losing access to every stored credential.
- **Credential route schema (migration 0004):** Route bindings split across `credentials.server_variables`, `credentials.scheme`, and a dedicated `credential_routes` table (not a single JSON blob on `credentials`).
- **Authentication model (two actors):** Humans authenticate with bcrypt password → 30-day sliding httpOnly JWT cookie. Agents authenticate with `X-Jentic-API-Key: tk_xxx` bound to a toolkit. There is no admin API key and no superuser env var — `docker exec` is the only superuser path. Root account creation is one-time (`POST /user/create` returns `410 Gone` after first use). New toolkit keys are always IP-restricted; the default allowlist is trusted subnets (RFC-1918 + loopback + `JENTIC_TRUSTED_SUBNETS` extras; the env var **appends**, never replaces). Privilege-escalation routes (approve/deny access requests, mutate toolkits, edit credential policies, manage OAuth brokers) require a human JWT session, so a compromised agent key cannot self-escalate via prompt injection. Endpoint-level detail in `docs/AUTH.md`.
- **Capability / Workflow ID format:** `METHOD/host/path` (e.g. `GET/api.stripe.com/v1/customers`). Workflows use the same format with `host = JENTIC_PUBLIC_HOSTNAME` (e.g. `POST/localhost/workflows/summarise-topics`), and operations vs workflows are distinguished by whether `host` matches `JENTIC_PUBLIC_HOSTNAME`. Agents persist these IDs — format stability is an API contract (see roadmap Phase 4).
- **Policy evaluation:** Toolkit policies evaluate allow/deny rules in order; first match wins; default-deny when no rule matches.
- **Content negotiation:** SPA routes return `index.html` for browser requests (`Accept: text/html`) and JSON for API clients; an extended middleware also supports YAML and Markdown responses. Implemented in `src/negotiate.py` and the SPA fallback in `main.py`.
- **UI ESLint guardrails:** Two rule sets — `src/components/ui/**` may define primitives (Button/Input/Select/Textarea); `src/pages/**` and `src/components/layout/**` must use those primitives instead of raw `<button>`/`<input>`/`<select>`/`<textarea>` and must use `AppLink` (not raw `<a>`). `@/` absolute imports are required (no parent relative paths). Enforced by `ui/eslint.config.js`.
- **Python import rule:** Top-level imports only. Inline imports are forbidden except to break circular imports (must be commented as such).
- **Agent collaboration rules:** Future SDD work must honor the rules in `.claude/rules/`.

## What We Are Not Using

- No **ORM** (SQLAlchemy, Tortoise, etc.) — raw `aiosqlite` SQL throughout `src/db.py`
- No **Redis or external cache** — all caching is in-memory or on-disk SQLite/file
- No **mypy or pyright** for Python type checking — not present in `pyproject.toml` dev deps
- No **CDN dependency** — Swagger UI, Redoc, and Tailwind runtime assets are vendored locally in `static/`
- No **PostCSS / tailwind.config.js** — TailwindCSS 4 is configured entirely in `ui/src/index.css` via `@theme inline` + CSS custom properties

## Open Questions / Uncertain Areas

- Python `arazzo-runner` is the interim engine; migration to the TypeScript implementation from `jentic-arazzo-tools` is a high-priority item on the roadmap (Phase 3)
- No rate limiting on any endpoint, including login and broker — pre-production requirement
- `api_keys` table is reserved for future fine-grained scope assignment; design not yet determined
- `auth_override_log` table exists in the baseline schema but its end-to-end usage and retention policy are not yet documented
- The `scheme_name` / `scheme_type` naming decision (see `docs/DECISIONS.md`) will affect credential-provisioning changes landing in Phase 6
