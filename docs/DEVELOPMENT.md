# Development Guide

## Hot Reload

uvicorn watches `/app/src/` (= `/mnt/jentic-pe/src/` on the host). Edit any `.py` file and the server reloads in ~1 second. No container restart needed.

To trigger a manual reload:
```bash
touch /mnt/jentic-pe/src/main.py
```

To watch reload logs:
```bash
docker logs -f openclaw-jentic-personal-edition-1 2>&1 | grep -E "reload|ERROR|WARNING"
```

---

## Testing Strategy

Jentic Mini has multi-layered testing that exercises different trust boundaries:

### Backend Tests (Python/pytest)

**Location:** `tests/`  
**Run:** `python3 -m pytest tests/ -v`  
**Philosophy:** Test at the HTTP boundary using a real temp SQLite database. No mocking of core functionality.

```bash
# Install test dependencies (includes production deps)
pip install -r requirements-dev.txt

# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_auth_boundary.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

**Test categories:**

| File | Purpose | What it validates |
|------|---------|-------------------|
| `test_auth_boundary.py` | Core auth enforcement | API key validation, human session checks, public vs protected endpoints |
| `test_auth_boundary_comprehensive.py` | Auth regression detector | Documents **current actual behavior** of all 68 operations — runtime vs OpenAPI spec mismatches, agent-accessible vs human-only operations |
| `test_openapi_contract.py` | OpenAPI spec quality | ui/openapi.json sync, metadata (contact, license, servers), explicit security declarations, Phase 1 requirements |
| `test_broker_contracts.py` | Broker behavior | Credential injection, upstream passthrough, error handling |
| `test_credential_vault.py` | Secrets management | Fernet encryption, no value leakage in responses |
| `test_policy_engine.py` | Access control rules | First-match-wins, regex path matching, method filtering |
| `test_toolkit_lifecycle.py` | Toolkit CRUD | Key generation, credential binding, counts |
| `test_health_and_meta.py` | Metadata endpoints | /health, /version responses |
| `test_oauth_broker_lifecycle.py` | OAuth delegation | Pipedream broker registration, account sync, connect links |

**Why no mocks?** The test suite uses a real SQLite database (with Alembic migrations) to catch integration issues that mocks would hide. Tests run in ~2 minutes — fast enough for tight TDD loops.

**OpenAPI contract tests** (`test_openapi_contract.py`) use Schemathesis to validate that API responses match the OpenAPI schema. Custom tests enforce Jentic-specific requirements (HTTPS first, explicit security, agent hints coverage).

**Auth boundary tests** (`test_auth_boundary_comprehensive.py`) document the **runtime enforcement** vs **OpenAPI spec declarations**. If this test fails, the auth boundary changed — verify it was intentional and update the test. Includes TODO markers for endpoints that may need stricter auth in the future.

### UI Tests (Vitest + Playwright)

**Location:** `ui/src/`  
**Run:** `cd ui && npm test`  
**Philosophy:** Browser-mode unit tests + MSW mocking + E2E with real backend.

```bash
cd ui

# Install dependencies
npm install

# Unit tests (Vitest browser mode + MSW)
npm test              # Watch mode
npm run test:run      # CI mode (single run)
npm run test:coverage # Istanbul coverage report

# E2E tests (Playwright)
npm run test:e2e         # Mocked backend (MSW)
npm run test:e2e:docker  # Real backend (requires server running)

# Linting (ESLint + Prettier)
npm run lint        # Check
npm run lint:fix    # Auto-fix
```

**Test stack:**
- **Vitest browser mode** — runs tests in real browsers via Playwright (Chrome, Firefox, Safari)
- **MSW (Mock Service Worker)** — intercepts HTTP calls to `/api/*` for isolated unit tests
- **Testing Library** — user-centric queries (`getByRole`, `getByLabelText`)
- **axe-core** — automated accessibility checks (WCAG violations fail tests)
- **Playwright E2E** — full integration tests against real backend

See `ui/TESTING.md` for the full UI testing guide.

### CI Pipeline

**Backend:** `.github/workflows/ci-backend.yml` (path-filtered: `src/`, `tests/`, `alembic/`)  
**UI:** `.github/workflows/ci-ui.yml` (path-filtered: `ui/`)  
**Docker:** `.github/workflows/ci-docker.yml` (always runs — validates build + E2E)

All three must pass before merge.

---

## Route Registration Order — CRITICAL

The broker is a catch-all (`/{target:path}`) that matches any path. It **must** be the last router registered in `main.py`. If registered earlier, it will swallow all JPE-internal routes.

**Required order in `main.py`:**

```python
# 1. All JPE routers (order among these doesn't matter)
app.include_router(capability_router)
app.include_router(workflows_router)
app.include_router(import_router)
app.include_router(traces_router)
app.include_router(overlays_router)
app.include_router(apis_router)
app.include_router(search_router)
app.include_router(creds_router)
app.include_router(collections_router)
app.include_router(policy_router)
app.include_router(permissions_router)
app.include_router(notes_router)
app.include_router(debug_router)

# 2. Health + root
@app.get("/health") ...
@app.get("/") ...

# 3. Docs + static
app.mount("/static", StaticFiles(directory="..."), name="static")

# 4. Broker — LAST
app.include_router(broker_router)
```

**Symptom of broken order:** JPE endpoints return broker errors like `No API found for host 'inspect'` instead of their normal responses.

---

## Adding a New API

### Option A: Via Import Endpoint (Recommended)

```bash
curl -X POST http://localhost:8900/import \
  -H "X-Jentic-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "api",
    "source": "url",
    "url": "https://raw.githubusercontent.com/APIs-guru/openapi-directory/main/APIs/stripe.com/2024-04-10/openapi.yaml"
  }'
```

JPE will:
1. Download the spec
2. Save it to `src/specs/`
3. Parse and register all operations in SQLite
4. Rebuild the BM25 index

### Option B: Manual Registration (Hidden Endpoint)

```bash
# 1. Download spec to the specs directory
curl -s "https://example.com/api/openapi.json" \
  > /mnt/jentic-pe/src/specs/myapi.json

# 2. Register via hidden POST /apis (admin key required)
curl -X POST http://localhost:8900/apis \
  -H "X-Jentic-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "api.myhost.com",
    "name": "My API",
    "description": "What this API does",
    "spec_path": "/app/src/specs/myapi.json",
    "base_url": "https://api.myhost.com"
  }'
```

Note: `spec_path` must be the **container-internal** path (`/app/...`), not the host mount path.

### Option C: Bulk Corpus Loader

For loading multiple APIs from the jentic/openapi-workflow-registry:

```bash
python3 /root/.openclaw/workspace/scripts/jpe_load_apis.py
```

This script downloads and registers a curated set of API specs. Check the script for configuration options.

---

## Rebuilding the BM25 Index

The index rebuilds automatically on import. For a manual rebuild (e.g. after direct DB manipulation):

```bash
curl -X POST http://localhost:8900/admin/rebuild-index \
  -H "X-Jentic-API-Key: $KEY"
```

---

## Docker Layout

| Path | Description |
|---|---|
| Container name | `openclaw-jentic-personal-edition-1` (check with `docker ps`) |
| Host config dir | `/configs/jentic-personal-edition/` |
| Compose file | `/configs/jentic-personal-edition/docker-compose.yml` |
| Source mount | `/configs/jentic-personal-edition/` → `/app/` in container |
| Data volume | `/configs/jentic-personal-edition/data/` → `/app/data/` |
| Specs | `/mnt/jentic-pe/src/specs/` = `/app/src/specs/` (same files) |

**Key path aliases:**
- `/mnt/jentic-pe/` = `/configs/jentic-personal-edition/` = `/app/` (inside container)
- These are the same directory; `/mnt/jentic-pe/` is just a convenience bind mount

### Common Docker commands

```bash
# Restart the service
cd /configs/jentic-personal-edition && docker compose restart

# View logs
docker logs -f openclaw-jentic-personal-edition-1

# Open a shell inside the container
docker exec -it openclaw-jentic-personal-edition-1 bash

# Run a Python script inside the container
docker exec -it openclaw-jentic-personal-edition-1 python3 /app/src/some_script.py

# Rebuild and restart (after Dockerfile changes)
cd /configs/jentic-personal-edition && docker compose up -d --build
```

---

## Accessing the Database

**From the host** (direct SQLite access):
```bash
sqlite3 /configs/jentic-personal-edition/data/jpe.db ".tables"
sqlite3 /configs/jentic-personal-edition/data/jpe.db "SELECT jentic_id, summary FROM operations LIMIT 10;"
```

Note: `/mnt/jentic-pe/data/` does NOT contain the database — only `/configs/jentic-personal-edition/data/` does (it's a Docker volume mount, not included in the git workspace bind).

**From inside the container:**
```bash
docker exec -it openclaw-jentic-personal-edition-1 sqlite3 /app/data/jpe.db ".tables"
```

**Useful queries:**
```sql
-- Count operations per API
SELECT api_id, COUNT(*) as ops FROM operations GROUP BY api_id ORDER BY ops DESC;

-- Find an operation by keyword
SELECT jentic_id, summary FROM operations WHERE summary LIKE '%voice%';

-- List workflows
SELECT slug, name, steps_count FROM workflows;

-- Check pending overlays
SELECT api_id, status, created_at FROM api_overlays WHERE status = 'pending';

-- Recent executions
SELECT id, workflow_id, operation_id, status, duration_ms, created_at
FROM executions ORDER BY created_at DESC LIMIT 20;
```

---

## Vendored Arazzo Runner

The arazzo-runner package is vendored at `/mnt/jentic-pe/vendor/arazzo-engine/`, branch `jpe-patches`.

**Do not** `pip install arazzo-runner` from PyPI inside the container — the vendored version contains JPE-specific patches that enable broker routing.

### Key patched files

| File | What was changed |
|---|---|
| `models.py` | `RuntimeParams` extended with `auth_headers` and `server_base_url` |
| `http.py` | `HTTPExecutor.execute_request` injects extra auth headers |
| `runner.py` | `ArazzoRunner.__init__` accepts `runtime_params`; `_apply_jpe_runtime_params()` rewrites server URLs |

### Upgrading the vendor fork

If you need a feature from a newer upstream arazzo-runner:

1. Check if it can be cherry-picked onto the `jpe-patches` branch
2. If yes: `cd /mnt/jentic-pe/vendor/arazzo-engine && git fetch origin && git cherry-pick <commit>`
3. If no: merge upstream `main` into `jpe-patches`, resolve conflicts, re-verify the patches still apply

**Never** replace the vendor fork with a fresh PyPI install without re-applying the patches.

---

## Debug Endpoints

These endpoints are registered but **hidden from the OpenAPI schema** (not shown in Swagger UI):

| Endpoint | Purpose |
|---|---|
| `GET /debug/env` | Show all environment variables (admin only) |
| `GET /debug/spec?api_id=...` | Inspect the loaded OpenAPI spec for an API |
| `GET /debug/arazzo-api` | Show the arazzo-runner package's public API |
| `GET /debug/env-mappings?spec_url=...` | Show credential env var mappings that would be used for a spec |

Example:
```bash
curl http://localhost:8900/debug/env \
  -H "X-Jentic-API-Key: $KEY"
```

---

## Adding a New Router

1. Create `src/routers/my_feature.py`
2. Define a `router = APIRouter(tags=["my-tag"])`
3. Add endpoints
4. Import and register in `main.py` **before** the broker:

```python
from routers.my_feature import router as my_feature_router
# ...
app.include_router(my_feature_router)  # before broker_router
```

5. Add the tag to `openapi_tags` in `main.py` if you want it to appear in a specific position in Swagger UI

---

## API Tag Taxonomy

JPE organises Swagger UI endpoints into these tags (in order):

1. `discover` — search and inspect (read-only catalog operations)
2. `execute` — broker + workflow execution
3. `observe` — traces and execution history
4. `collections` — collection management
5. `permissions` — permission requests and escalation
6. `credentials` — credential management (admin)
7. `catalog` — API and workflow registration (admin)

When adding a new endpoint, pick the most appropriate tag. This ordering is intentional: it mirrors the agent workflow (discover → execute → observe) and puts the most commonly-used endpoints first in the UI.

---

## Testing a Workflow End-to-End

```bash
export KEY="your-admin-key-from-docker-compose"

# 1. Check the workflow is registered
curl http://localhost:8900/workflows/summarise-latest-topics \
  -H "X-Jentic-API-Key: $KEY" | python3 -m json.tool

# 2. Inspect it (shows inputs, steps, links)
curl "http://localhost:8900/inspect/POST%2Flocalhost%2Fworkflows%2Fsummarise-latest-topics" \
  -H "X-Jentic-API-Key: $KEY" | python3 -m json.tool

# 3. Execute it
curl -X POST http://localhost:8900/localhost/workflows/summarise-latest-topics \
  -H "X-Jentic-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

# 4. Check the trace
TRACE_ID="uuid-from-step-3"
curl http://localhost:8900/traces/$TRACE_ID \
  -H "X-Jentic-API-Key: $KEY" | python3 -m json.tool
```

---

## Design Doc References

Before implementing new features, consult the authoritative v2 API design documents:

- `/root/.openclaw/workspace/docs/jentic/jentic-api-design/shirka-v2-proposal.md`
- `/root/.openclaw/workspace/docs/jentic/jentic-api-design/requirements.md`

These define the intended final API shape. JPE is the implementation proving that design works.
