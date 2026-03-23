# Jentic Mini

**Jentic Mini** is the open-source, self-hosted implementation of the Jentic API — fully API-compatible with the [Jentic hosted and VPC editions](https://jentic.com).

## What is Jentic Mini?

Jentic Mini gives any AI agent a local execution layer:

- **Search** — find the right API operation or workflow from a registered catalog using full-text BM25 search
- **Execute** — broker authenticated requests through any registered API without ever exposing credentials to the agent
- **Observe** — inspect execution traces, async job handles, and audit logs
- **Toolkits** — define scoped access policies and credential bundles for agents (one toolkit key per agent, individually revocable)
- **Credentials vault** — store API keys, OAuth tokens, and secrets in an encrypted local vault; they're injected at execution time and never returned via the API
- **Public catalog** — browse and import from 1,044 OpenAPI specs and 380 Arazzo workflow sources in the [Jentic public catalog](https://github.com/jentic/jentic-public-apis); specs and workflows are imported automatically when you add credentials

## Hosted vs Self-hosted

The **Jentic hosted and VPC editions** offer deeper implementations across four areas:

| Capability | Jentic Mini (this) | Jentic hosted / VPC |
|------------|-------------------|---------------------|
| **Search** | BM25 full-text search | Advanced semantic search (~64% accuracy improvement over BM25) |
| **Request brokering** | In-process credential injection | Scalable AWS Lambda-based broker with encryption at rest and in-transit, SOC 2-grade security, and 3rd-party credential vault integrations (HashiCorp Vault, AWS Secrets Manager, etc.) |
| **Simulation** | Basic simulate mode | Full sandbox for simulating API calls and toolkit behaviour (enterprise-only) |
| **Catalog** | ~1,044 APIs + ~380 workflow sources from [jentic-public-apis](https://github.com/jentic/jentic-public-apis); auto-imported on credential add | Central catalog — aggregates the collective know-how of agents across API definitions and Arazzo workflows |

Jentic Mini is designed to be a fully compatible entrypoint: build your agent integrations against Jentic Mini locally, then point at the hosted API for production.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local dev without Docker)

### Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `JENTIC_API_KEY` | `changeme` | Master admin key — change this |
| `JENTIC_VAULT_KEY` | auto-generated | Fernet key for the credentials vault |
| `JENTIC_PUBLIC_HOSTNAME` | `localhost:8900` | Public hostname used in generated URLs |
| `DB_PATH` | `/app/data/jentic-mini.db` | SQLite database path |

### Running

```bash
# Build and start
docker compose build
docker compose up -d
```

> **Note:** If running from a directory other than the project root, set `JENTIC_HOST_PATH` to the project path:
> `JENTIC_HOST_PATH=/path/to/jentic-mini docker compose up -d`

API available at `http://localhost:8900`. Swagger UI at `http://localhost:8900/docs`.

### Authentication

All endpoints require `X-Jentic-API-Key`:

- **Master key** (`JENTIC_API_KEY`): full admin access — use for setup only
- **Toolkit key** (`tk_xxx`): scoped to a toolkit's credentials and policy — give this to agents

Typical agent setup:
1. Admin creates a toolkit (master key): `POST /toolkits`
2. Admin creates credentials in the vault: `POST /credentials`
3. Admin grants credentials to the toolkit: `POST /toolkits/{id}/credentials`
4. Admin generates a toolkit access key: `POST /toolkits/{id}/keys`
5. Agent uses the `tk_xxx` key for all subsequent calls

## API Overview

| Tag | Who uses it | Purpose |
|-----|-------------|---------|
| **search** | Agents | Full-text search — the main entrypoint |
| **discover** | Agents | Inspect capabilities, list APIs and operations |
| **execute** | Agents | Transparent request broker — runs API operations and Arazzo workflows |
| **toolkits** | Agents/Humans | Toolkits, access keys, policies, permission requests |
| **observe** | Agents | Read execution traces |
| **catalog** | Humans/admin | Register APIs, browse public catalog, upload specs, overlays, notes |
| **credentials** | Humans only | Manage the credentials vault; adding credentials auto-imports catalog specs and workflows |

## Public Catalog

Jentic Mini is connected to the [Jentic public API catalog](https://github.com/jentic/jentic-public-apis) — ~1,044 API specs and ~380 Arazzo workflow sources.

The catalog manifest is fetched lazily at startup (two GitHub API calls) and cached locally for 24 hours. Specs and workflows are imported **automatically** the first time you add credentials for a catalog API.

```http
# Just add credentials — Jentic Mini handles the rest
POST /credentials
{ "api_id": "slack.com", "scheme_name": "BearerAuth", "values": { "token": "xoxb-..." } }

# Slack's 17 workflows and its full API spec are now in your local registry
GET /workflows?source=local&q=slack
```

See [docs/CATALOG.md](docs/CATALOG.md) for full details.

## Architecture

- **FastAPI + uvicorn** — async HTTP server with hot reload in dev
- **SQLite** — local registry, toolkit/key store, execution log
- **BM25** — in-memory full-text search index over operation descriptions
- **Fernet** — symmetric encryption for the credentials vault
- **arazzo-runner** — Arazzo workflow execution engine

## License

Apache 2.0
