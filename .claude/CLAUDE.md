# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Jentic Mini?

Jentic Mini is the open-source, self-hosted implementation of the Jentic API. It gives AI agents a local execution layer: search APIs via BM25, broker authenticated requests (credential injection without exposing secrets to the agent), enforce access policies, and observe execution traces. Built with FastAPI + SQLite + Fernet encryption.

## Running the Server

```bash
docker compose up -d
```

API at `http://localhost:8900`, Swagger UI at `http://localhost:8900/docs`.

### Development workflow
- **Python changes**: `src/` is volume-mounted into the container. Uvicorn auto-reloads on any `.py` file change — no container restart needed.
- **UI changes**: `cd ui && npm install && npm run dev` for Vite dev server with HMR on port 5173 (proxies API calls to the container on 8900).
- **Rebuild UI in Docker**: `cd ui && npm run build`, then `docker compose up -d --build`.

### Key environment variables
- `JENTIC_VAULT_KEY` — Fernet key for credentials vault (auto-generated from `data/vault.key` if unset)
- `JENTIC_PUBLIC_HOSTNAME` — public hostname for self-links and workflow dispatch
- `DB_PATH` — SQLite database path (default: `/app/data/jentic-mini.db`)
- `LOG_LEVEL` — `debug | info | warning | error`
- `JENTIC_HOST_PATH` — project root path for Docker mounts (defaults to `.`)

## Architecture

### Request flow
All requests pass through `APIKeyMiddleware` (`src/auth.py`) which validates `X-Jentic-API-Key` and sets `request.state.toolkit_id` / `request.state.is_admin`.

### Broker catch-all pattern (CRITICAL)
The broker router (`src/routers/broker.py`) is a catch-all `/{target:path}` that proxies requests to upstream APIs. It identifies broker routes by checking if the first path segment contains a `.` (e.g., `api.stripe.com`).

**The broker MUST be the last router registered in `src/main.py`.** If registered before other routers, it swallows all internal routes. Symptom: endpoints return broker errors like `No API found for host 'inspect'`.

Registration order in `src/main.py`:
1. All internal routers (capability, workflows, import, catalog, jobs, traces, overlays, apis, search, credentials, toolkits, etc.)
2. Health, root, favicon, login, docs, redoc routes
3. Static file mounts + SPA catch-all routes
4. `broker_router` — **last**

### Core modules (`src/`)
| File | Purpose |
|------|---------|
| `config.py` | Centralised constants: `DB_PATH`, `JENTIC_PUBLIC_HOSTNAME`, `SPECS_DIR`, `WORKFLOWS_DIR`, `DEFAULT_TOOLKIT_ID` |
| `main.py` | FastAPI app, router registration, lifespan, OpenAPI schema customization |
| `auth.py` | API key middleware — validates `X-Jentic-API-Key` header |
| `db.py` | SQLite schema init + migrations (aiosqlite) |
| `bm25.py` | In-memory BM25 search index over operations and workflows |
| `vault.py` | Fernet-encrypted credential storage |
| `oauth_broker.py` | OAuth broker registry for delegated auth flows |
| `models.py` | Pydantic models |
| `validators.py` | Input validation |
| `negotiate.py` | Content negotiation middleware |
| `startup.py` | Self-registration + broker app seeding at startup |
| `utils.py` | Shared utilities (`_abbreviate()`, `build_absolute_url()`, `parse_prefer_wait()`) |

### Routers (`src/routers/`)
| Router | Tag | Key responsibility |
|--------|-----|--------------------|
| `search.py` | search | BM25 full-text search — main agent entrypoint |
| `capability.py` | inspect | `GET /inspect/{id}` — operation/workflow details |
| `broker.py` | execute | Catch-all proxy with credential injection |
| `workflows.py` | execute | Workflow listing + execution via arazzo-runner |
| `toolkits.py` | toolkits | Toolkit CRUD, access keys, policies |
| `credentials.py` | credentials | Credential vault management (admin) |
| `traces.py` | observe | Execution trace retrieval |
| `apis.py` | catalog | API registration, spec management |
| `catalog.py` | catalog | Public catalog browsing (jentic-public-apis) |
| `import_.py` | catalog | Spec/workflow import endpoint |
| `overlays.py` | catalog | Security scheme overlay management |
| `jobs.py` | observe | Async job handles |
| `default_key.py` | — | First-time key generation from trusted subnet |
| `user.py` | user | Human account management + JWT auth |
| `oauth_brokers.py` | credentials | OAuth broker configuration |

### Credential injection flow
Credentials are **never** exposed to agents or passed as env vars. The broker:
1. Identifies upstream host from the URL path
2. Looks up credentials bound to the requesting toolkit
3. Reads the security scheme from the spec + any confirmed overlays
4. Injects the auth header (reads scheme name from overlay, not hardcoded)
5. Forwards to the real upstream
6. Logs a trace

### Workflow execution
Arazzo workflows use `arazzo-engine` (cloned at Docker build time from `github.com/jentic/arazzo-engine`). The runner patches `servers[0].url` in source specs to route all HTTP calls through the local broker (`http://localhost:8900/{host}`), ensuring every step gets credential injection, tracing, and policy enforcement.

### ID formats
- **Capability ID**: `METHOD/host/path` (e.g., `GET/api.elevenlabs.io/v1/voices`)
- **Workflow ID**: `POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/{slug}`
- The system distinguishes operations from workflows by checking if the host matches `JENTIC_PUBLIC_HOSTNAME`

### Database
SQLite with aiosqlite. Schema defined in `src/db.py` with inline migrations. Key tables: `apis`, `operations`, `credentials`, `toolkits`, `toolkit_keys`, `toolkit_credentials`, `workflows`, `executions`, `execution_steps`, `api_overlays`, `notes`, `permission_requests`.

### OAuth brokers (`src/brokers/`)
Pluggable OAuth broker system. Currently includes `pipedream.py` for Pipedream-based OAuth credential routing.

## UI

The `ui/` directory contains a React 18 + Vite 5 admin frontend.

### Tech stack
- **TailwindCSS 4** via `@tailwindcss/vite` plugin (no PostCSS, no JS config file)
- **Design tokens**: Single-file theme in `ui/src/index.css` using the shadcn/TW4-native pattern:
  - `@theme inline` maps CSS custom properties to Tailwind utility classes (e.g. `--color-primary: var(--primary)` → `bg-primary`, `text-primary`)
  - `:root` defines the full HSL color palette and semantic mappings
  - `@layer base` sets body, heading, and button cursor styles
- **Icons**: Lucide React (SVG components, no emoji)
- **Fonts**: Sora (body), Nunito Sans (headings), Geist Mono (code) — loaded via Google Fonts in `index.html`

### Build
- **Build output**: `static/` at project root (gitignored, generated at build time)
- **Static path resolution**: `src/main.py` resolves `STATIC_DIR` to `<project_root>/static/`. In Docker this is `/app/static/` (outside the `./src:/app/src` bind mount, so dev mounts don't hide built assets).
- **Docker**: Multi-stage build — Node stage compiles UI to `static/`, Python stage runs the server. Final image has no Node/npm.
- **Vite plugin** (`copyApiDocsAssets` in `ui/vite.config.ts`): copies `swagger-ui-dist` and `redoc` assets from `node_modules` into `static/` after each build, so `/docs` and `/redoc` work offline.
- **Favicon**: lives in `ui/public/favicon.png`, Vite copies it to output automatically.

### Adding colors or tokens
All theming is in `ui/src/index.css`. To add a new semantic color:
1. Add the raw HSL value to `:root` (e.g. `--info: hsl(210 80% 60%)`)
2. Add the semantic mapping to `:root` if needed (e.g. `--info-foreground: hsl(0 0% 100%)`)
3. Map it in `@theme inline` (e.g. `--color-info: var(--info)`)
4. Use it in components as `bg-info`, `text-info`, etc.

## Data directory (all gitignored)
- `data/jentic-mini.db` — SQLite database
- `data/vault.key` — Fernet encryption key (auto-generated)
- `data/specs/` — Downloaded API specs
- `data/catalog_manifest.json` — Cached public catalog manifest
- `data/workflow_manifest.json` — Cached workflow manifest
- `data/workflows/` — Imported workflow files