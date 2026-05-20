# Development Setup

## Prerequisites

- **Python 3.11+**
- **uv** (Python package manager):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh      # Linux / macOS
  ```
  Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Node.js 24+** and **npm** (for the UI)
- **Docker** and **Docker Compose** (for running the server)
- **GitHub CLI** (`gh`) — https://cli.github.com/

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/jentic/jentic-mini.git
cd jentic-mini
```

### 2. Install dependencies

```bash
uv sync
```

uv creates the project-local `.venv` automatically and installs all runtime and dev dependencies.

### 3. Install UI dependencies

```bash
cd ui
npm install
```

### 4. Run the server (Docker)

There are two compose files:

- **`compose.yml`** — base configuration (production-like)
- **`compose.dev.yml`** — adds Vite dev server with HMR on port 5173

```bash
docker compose up -d                                  # base only
docker compose -f compose.yml -f compose.dev.yml up   # with UI dev server
```

Export `JENTIC_UID=$(id -u)` and `JENTIC_GID=$(id -g)` (same shell line as `docker compose ...`) whenever your workstation UID/GID differs from Compose’s defaults (**1000:1000**) — notably on Linux, so `./ui`, `./src`, and `./data` stay owned by your user for both **jentic-mini** and **vite** (`compose.dev.yml` passes the same values through).

The API is available at `http://localhost:8900` and the Swagger UI at `http://localhost:8900/docs`.

### 5. UI development (optional)

For frontend development with hot module replacement outside Docker:

```bash
cd ui
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies API calls to the backend on port 8900.

### 6. Claude Code plugins (optional)

If you use Claude Code, this repo expects the `skill-creator` plugin (listed under `enabledPlugins` in `.claude/settings.json`). The marketplace is built-in, so one command installs it:

```
/plugin install skill-creator@claude-plugins-official
```

`enabledPlugins` only activates an already-installed plugin — it does not install it. Skip this step if you don't use Claude Code.

## Day-to-day Development

- **Python changes**: `src/` is volume-mounted into the container. Uvicorn auto-reloads on any `.py` file change — no container restart needed.
- **UI changes**: Use `npm run dev` in `ui/` for Vite HMR.
- **Rebuild UI in Docker**: `cd ui && npm run build`, then `docker compose up -d --build`.

## Running Tests

### Backend

```bash
uv run poe test                                         # all tests
uv run poe test tests/test_auth_boundary.py             # specific file
uv run poe test tests/test_auth_boundary.py -- -v       # with extra flags
uv run poe test tests -- -k "policy and not deny"       # -k name filter
uv run poe test tests -- --cov=src --cov-report=html    # with coverage
```

The first positional argument is the test target (default: `tests`); pass extra pytest flags after `--`.

### UI

```bash
cd ui
npm test              # Vitest watch mode
npm run test:run      # Single CI run
npm run test:e2e      # Playwright E2E tests (mocked)
npm run test:e2e:docker  # Docker E2E (real backend)
```

## Linting

### Backend

```bash
uv run poe lint       # Ruff check + format check
uv run poe lint:fix   # Auto-fix
uv run poe            # List all available tasks
```

### UI

```bash
cd ui
npm run lint          # ESLint check (includes Prettier)
npm run lint:fix      # Auto-fix
```

## Rebuilding the BM25 index

The index rebuilds automatically on import. To force a rebuild (e.g. after direct DB edits):

```bash
curl -X POST http://localhost:8900/admin/rebuild-index \
  -H "X-Jentic-API-Key: $KEY"
```

## Debug endpoints

These live in `src/routers/debug.py` and are hidden from the OpenAPI schema. Useful for poking at the running server:

| Endpoint | Purpose |
|---|---|
| `GET /debug/whoami` | IP detection diagnostics — verify the client IP isn't masked by Docker / reverse proxy |
| `GET /debug/auth-internals` | Dump `arazzo_runner`'s internal credential-model source — useful when the upstream package restructures |
| `GET /debug/spec?path=...` | Summarise an OpenAPI spec file under `data/` (path count, security schemes, sample ops) |
| `GET /debug/env-mappings?arazzo_path=...` | Show which credential env vars arazzo-runner would expect for a given Arazzo file |
| `GET /debug/vault-status` | Vault key source + round-trip encrypt/decrypt smoke test |
| `GET /debug/pycheck` | Python package availability check |
| `GET /debug/broker-cred-test?host=...` | Test broker credential lookup for a given host |
