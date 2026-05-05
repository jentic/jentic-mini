# Jentic Mini Architecture

## System Overview

Jentic Mini is a FastAPI service with four primary responsibilities:

| Responsibility | What it does |
|---|---|
| **Catalog** | Stores registered APIs (OpenAPI specs) and Arazzo workflows in SQLite; indexes them with BM25 for natural language search |
| **Broker** | Transparent HTTP reverse proxy — URL pattern `/{upstream_host}/{path}`, injects credentials automatically, enforces toolkit policies |
| **Workflow orchestrator** | Executes Arazzo multi-step workflows via `arazzo-runner`; each step routes through the broker for credential injection |
| **Credential vault** | Fernet-encrypted SQLite store; credentials are write-only (values never returned after creation) |
| **Workflow renderer** | React-based visualization via `@jentic/arazzo-ui` (npm package from [jentic-arazzo-tools](https://github.com/jentic/jentic-arazzo-tools)); provides diagram, docs, and split views |

Additionally:
- **Toolkits**: scoped credential bundles with their own API keys, access policies, and per-key IP restrictions
- **Access control**: policy rules (allow/deny) evaluated at broker time; agent permission escalation flow

---

## Component Map

```
Client (agent or human)
    │
    │  X-Jentic-API-Key header
    ▼
┌─────────────────────────────────────────────────────┐
│  API Key Middleware  (auth.py)                       │
│  Sets: request.state.toolkit_id                     │
│        request.state.toolkit_key_id                 │
│        request.state.is_admin                       │
│        request.state.is_human_session               │
│        request.state.simulate                       │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI Router  (main.py)                          │
│                                                     │
│  Registration order (CRITICAL — see below):         │
│                                                     │
│  capability_router    → GET /inspect/{id}           │
│  workflows_router     → GET/POST /workflows/...     │
│  import_router        → POST /import                │
│  catalog_router       → /catalog/...               │
│  jobs_router          → /jobs/...                  │
│  traces_router        → GET /traces/...             │
│  overlays_router      → POST /apis/{id}/scheme      │
│                          POST /overlays             │
│  apis_router          → GET /apis/...               │
│  search_router        → GET /search                 │
│  creds_router         → /credentials               │
│  toolkits_router      → /toolkits/...              │
│  policy_router        → /toolkits/{id}/policy      │
│  access_requests      → /toolkits/{id}/access-requests │
│  notes_router         → /notes                     │
│  debug_router         → /debug/...  (hidden)        │
│  user_router          → /user/...                  │
│  default_key_router   → /default-api-key/...       │
│  oauth_brokers_router → /oauth-brokers/...         │
│  ── static mount (/static) ──                       │
│  broker_router        → /{upstream_host}/{path}  ◄─ LAST │
└─────────────────────────────────────────────────────┘
    │                           │
    │ Internal routes           │ Broker routes
    ▼                           ▼
┌──────────────┐     ┌─────────────────────────────────┐
│ SQLite DB    │     │ Upstream API                    │
│ (db.py)      │     │  - credential injected          │
│              │     │  - policy checked               │
│ BM25 index   │     │  - trace logged                 │
│ (bm25.py)    │     │  - overlay confirmed on 2xx     │
└──────────────┘     └─────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Broker URL Pattern

Pattern: `/{upstream_host}/{path}`

Examples:
- `/api.stripe.com/v1/customers`
- `/api.elevenlabs.io/v1/voices`
- `/slack.com/api/chat.postMessage`

No protocol scheme prefix. No special prefix like `/proxy/`. The broker is a catch-all registered **last** in `main.py`. It self-identifies by checking whether the first path segment contains a dot (`.`). All Jentic-internal routes take priority because they are registered first.

This means agents call external APIs exactly as `/{host}/{path}` — the same format as Capability IDs but without the `METHOD/` prefix.

### 2. Capability IDs

Format: `METHOD/host/path`

Examples:
- `GET/api.elevenlabs.io/v1/voices`
- `POST/api.openai.com/v1/chat/completions`
- `DELETE/api.github.com/repos/{owner}/{repo}`

Rules:
- No protocol scheme
- No spaces
- Single slash as separator between method, host, and path segments
- Unambiguous: HTTP methods never start with a dot; hostnames never start with uppercase
- Stored in `operations.jentic_id` column

### 3. Workflow IDs

Same format as Capability IDs, using the Jentic hostname:

`POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/{slug}`

The backend infers "is this an operation or a workflow?" by checking whether the host matches `JENTIC_PUBLIC_HOSTNAME`. If yes → workflow dispatch. If no → broker proxy.

This means the `/inspect/{id}` endpoint and `/search` results use a single ID format for both operations and workflows — agents don't need to know which type they're dealing with until execution time.

### 4. Credential Injection via Broker

**Credentials are NEVER passed as env vars to the arazzo-runner subprocess.**

Instead, Jentic Mini preprocesses each source spec before invoking `arazzo-runner`, rewriting `servers[0].url` to `http://localhost:8900/{host}`. This routes every step through the local broker, which:

1. Identifies the upstream host from the rewritten URL
2. Looks up credentials in the current toolkit bound to that API
3. Injects the appropriate auth header
4. Forwards the request to the real upstream
5. Logs the result as a trace

Benefits:
- Single chokepoint for credential injection
- All workflow steps are logged as traces
- Policy is enforced on every step
- Credentials never exist in subprocess environment

### 5. Security Scheme Overlays (Auth Flywheel)

Many real-world OpenAPI specs have incorrect or absent security schemes. Jentic Mini handles this with a flywheel pattern:

1. Agent tries a broker call → broker returns 400 with an example `POST /apis/{api_id}/scheme` call
2. Agent calls `POST /apis/{api_id}/scheme` with auth type + config → creates a **pending overlay**
3. Agent creates a credential bound to that `api_id` + `scheme_name`
4. Agent retries the broker call → broker injects the header
5. On HTTP 2xx → overlay status automatically flips to **confirmed**

Confirmed overlays are merged with the API's OpenAPI spec at broker time. The first agent to figure out auth for an API contributes it for all future agents using that toolkit.

### 6. Toolkits

A toolkit is a named bundle of credentials with access keys. Key properties:

- Each toolkit has one or more keys (`toolkit_keys` table), one per agent/client
- Keys are individually revocable (soft delete via `revoked_at`)
- Per-key IP restrictions (CIDR array in `allowed_ips`)
- Per-toolkit policy rules (allow/deny, first-match-wins)
- The `default` toolkit is created automatically at first setup
- Agent keys use the prefix `tk_`

Credential binding: credentials are stored globally but scoped per-toolkit via the `toolkit_credentials` join table. A broker request only injects credentials bound to the requesting toolkit.

### 7. Route Registration Order Is Critical

The broker catches `/{target:path}` — any path that isn't matched by an earlier route. If registered before internal routers, it would swallow all internal endpoints.

**Required order in `main.py`:**
1. All internal routers (capability, workflows, import, catalog, jobs, traces, overlays, apis, search, credentials, toolkits, policy, access-requests, notes, debug, user, default-key, oauth-brokers)
2. `/health` and `/` routes
3. `/docs`, `/redoc`, static mount
4. `broker_router` — **last**

Breaking this order is a silent failure: internal endpoints become unreachable and return broker errors.

### 8. Swagger UI Served Locally

Swagger/Redoc assets are installed from npm packages (`swagger-ui-dist`, `redoc`) and copied into `static/` at build time by the Vite `copyApiDocsAssets` plugin.

This allows the service to work fully offline and on patchy connections. No CDN dependency.

---

## Conceptual Data Model

Database: SQLite at `/app/data/jentic-mini.db` (inside container).

**Exact schema lives in Alembic migrations** under `alembic/versions/`. `src/db.py` only opens connections and runs `run_migrations()` at startup. This document intentionally describes the **data model and relationships**, not the full column-by-column schema.

### Core domains

| Domain | Main records | Purpose |
|---|---|---|
| **Catalog** | `apis`, `operations`, `workflows` | Stores imported OpenAPI specs, extracted operations, and registered Arazzo workflows |
| **Credentials & routing** | `credentials`, `credential_routes`, `api_broker_apps` | Stores encrypted credentials plus the host/path routing metadata the broker uses to select them |
| **Toolkits & access** | `toolkits`, `toolkit_keys`, `toolkit_credentials`, `toolkit_policies`, `credential_policies`, `permission_requests` | Groups credentials per agent, issues revocable keys, and enforces allow/deny policy with human escalation |
| **Execution & jobs** | `executions`, `execution_steps`, `jobs` | Persists operation traces, workflow step traces, and async job state |
| **Catalog patches & feedback** | `api_overlays`, `notes`, `auth_override_log` | Records agent-contributed auth overlays, notes, and auth-discovery evidence |
| **Human/admin setup** | `users`, `settings` | Stores human accounts and instance-level setup state |
| **OAuth broker integration** | `oauth_brokers`, `oauth_broker_accounts`, `oauth_broker_connect_labels` | Stores managed OAuth broker configuration and connected upstream accounts |

### Architecturally important relationships

- An **API** has many **operations**.
- A **workflow** references one or more APIs via `involved_apis`, but executes as its own first-class capability.
- **Credentials** are stored globally, but a toolkit can only use credentials bound to it through `toolkit_credentials`.
- The broker resolves credentials primarily through **`credential_routes`** (host + path prefix), not by directly scanning API registrations.
- A **toolkit** can issue multiple **toolkit keys**, each independently revocable and optionally IP-restricted.
- **Toolkit policies** and **credential policies** are evaluated at broker time before the vault is touched.
- Every brokered operation or workflow execution writes an **execution trace**; workflow runs also write **execution step** records.
- Async execution persists state in **`jobs`**, which can point back to traces.
- **API overlays** are stored separately from the base spec and merged at read/broker time once confirmed.

### Design implications

- The database is used for both **registry state** (catalog, credentials, toolkits) and **operational state** (traces, jobs, setup flags).
- Schema evolution is expected; prose docs should not be treated as the schema source of truth.
- If you need exact columns, defaults, or migration order, read `alembic/versions/0001_baseline.py` and later revisions directly.

---

## BM25 Search Index

The search index is in-memory, built at startup from all registered operations and workflows.

**Implementation:** `bm25.py` — uses the `rank_bm25` library.

**What gets indexed:**

- **Operations**: `summary` + `description` + `path` + `method` + vendor name (`_vendor` extracted at import time)
- **Workflows**: `name` + `summary` + `description` + `involved_apis`

**When it's rebuilt:**
- On service startup
- After `POST /import` (new API or workflow registered)
- After `POST /apis` (hidden endpoint)
- On `POST /admin/rebuild-index` (explicit admin trigger)

**Search result fields:**

```json
{
  "id": "GET/api.elevenlabs.io/v1/voices",
  "type": "operation",
  "summary": "List voices",
  "description": "Get all available voices. Returns voice metadata including voice_id...",
  "score": 4.72,
  "_links": {
    "inspect": "/inspect/GET%2Fapi.elevenlabs.io%2Fv1%2Fvoices",
    "execute": "/api.elevenlabs.io/v1/voices"
  }
}
```

Description is abbreviated to ≤3 sentences by `utils.abbreviate()` to keep search results token-efficient for LLM consumers.

---

## Arazzo Runner

**Source:** Installed from PyPI (`arazzo-runner` package).

The arazzo-runner executes workflows via a `requests.Session` with the caller's API key as a default header, routing all HTTP calls through the broker for credential injection.

### Preprocessing in `workflows.py`

Before handing the Arazzo spec to the runner, `workflows.py`:
1. Reads the source spec from disk
2. For each `sourceDescriptions` entry, rewrites `servers[0].url` to `http://localhost:8900/{host}` in a **temp copy**
3. Passes the temp copy path to `ArazzoRunner`

This ensures every step's HTTP call goes to `localhost:8900` (the broker) rather than directly to the upstream API. The broker then injects credentials, logs traces, and enforces policy before forwarding.

**Why a temp copy?** The original spec file must not be modified. The rewrite is per-execution and ephemeral.

---

## Request Lifecycle

### Single Operation Call (Broker)

```
Client: GET /api.elevenlabs.io/v1/voices
  → auth.py: validates X-Jentic-API-Key, sets toolkit_id
  → broker.py: first segment "api.elevenlabs.io" contains dot → broker route
  → check policy: does this toolkit allow GET/api.elevenlabs.io/v1/voices?
  → if simulate=true: return mock 200 {}
  → find API registration for api.elevenlabs.io
  → find credentials in this toolkit for api.elevenlabs.io
  → find confirmed overlays for api.elevenlabs.io
  → merge security schemes from spec + overlays
  → build auth header (e.g. xi-api-key: sk-...)
  → forward request to https://api.elevenlabs.io/v1/voices with injected header
  → receive response
  → write trace to executions table
  → if overlay pending and response 2xx: confirm overlay
  → return response to client
```

### Workflow Execution

```
Client: POST /{JENTIC_PUBLIC_HOSTNAME}/workflows/summarise-latest-topics
  → auth.py: validates key
  → broker.py: host = JENTIC_PUBLIC_HOSTNAME → internal dispatch
  → workflows.py: dispatch_workflow("summarise-latest-topics", inputs, toolkit_id)
  → read arazzo spec from disk
  → apply input schema defaults
  → preprocess: rewrite server URLs to localhost:8900/{host}
  → spawn arazzo-runner subprocess
  → runner executes step 1: GET /techpreneurs.ie/latest.json
      → hits broker at localhost:8900
      → broker injects credentials (if any), logs trace
      → returns response to runner
  → runner executes step 2: POST /api.openai.com/v1/chat/completions
      → hits broker at localhost:8900
      → broker injects OpenAI bearer token, logs trace
      → returns response to runner
  → runner returns outputs
  → write execution + execution_steps to DB
  → return {status, slug, outputs, step_outputs, trace_id, _links}
```
