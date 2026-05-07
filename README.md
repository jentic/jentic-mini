<p align="center">
  <a href="https://jentic.com/mini"><img src="https://raw.githubusercontent.com/jentic/jentic-mini/main/assets/jentic-mini-logo.svg" alt="Jentic Mini" width="400"></a>
</p>

<a href="https://www.producthunt.com/products/jentic-mini?embed=true&utm_source=badge-featured&utm_medium=badge&utm_campaign=badge-jentic-mini" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1107386&theme=light&t=1775041287603" alt="Jentic&#0032;Mini - Give&#0032;your&#0032;AI&#0032;agents&#0032;safe&#0032;access&#0032;to&#0032;10&#0044;000&#0043;&#0032;APIs | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>

Give your AI agents access to **10,000+ APIs** — without leaking a single credential.
Building agents that call real APIs is painful. You end up hardcoding auth, juggling secrets in prompts,
writing bespoke glue code for every service, and praying nothing leaks. Jentic Mini fixes this.
It's a self-hosted API execution layer that sits between your agent and the outside world.
Your agent says what it wants to do. Jentic Mini handles the how — finding the right API,
injecting credentials at runtime, and brokering the request. Secrets never touch the agent. Ever.

> ⚠️ **Early Access** — Jentic Mini is new and under active development. It may contain bugs, rough edges, and security gaps we haven't found yet. It is **not recommended for production use** at this stage. We're sharing it early so the community can explore it, test it, and help shape it. Use it in personal or development environments, and please [report issues](https://github.com/jentic/jentic-mini/issues) as you find them.

## Quick Start

**Using OpenClaw?** The fastest way to get started is via the Jentic skill on [ClawHub](https://clawhub.com) — it will guide you through your installation options and connect your agent automatically. Just tell your OpenClaw agent:

> "install and set up the jentic skill from ClawHub"

**Want the full stack on a fresh VPS?** [jentic-quick-claw](https://github.com/jentic/jentic-quick-claw) installs OpenClaw, Jentic Mini, Mattermost, and a file browser in one command — everything pre-wired and secured via Tailscale.

**Just want Jentic Mini standalone?** See [Getting Started](#getting-started) below.

**Already running?** Jump to the [hands-on tutorial](docs/tutorials/01-notion-permissions.md) — connect the Notion API, see the permissions model in action, and have your agent create pages with controlled access.

## What is Jentic Mini?

**Jentic Mini** is the open-source, self-hosted implementation of the Jentic API — fully API-compatible with the [Jentic hosted and VPC editions](https://jentic.com).

---

<p align="center">
  <img src="https://raw.githubusercontent.com/jentic/jentic-mini/main/assets/architecture-light.svg" alt="Jentic Mini Architecture" width="800">
</p>

---

Jentic Mini gives any AI agent a local execution layer:

- **Search** — find the right API operation or workflow from a registered catalog using full-text BM25 search
- **Execute** — broker authenticated requests through any registered API without ever exposing credentials to the agent
- **Observe** — inspect execution traces, async job handles, and audit logs
- **Toolkits** — define scoped access policies and credential bundles for agents (one toolkit key per agent, individually revocable)
- **Credentials vault** — store API keys, OAuth tokens, and secrets in an encrypted local vault; they're injected at execution time and never returned via the API
- **Public catalog** — browse and import from 10,000+ OpenAPI specs and 380 Arazzo workflow sources in the [Jentic public catalog](https://github.com/jentic/jentic-public-apis); specs and workflows are imported automatically when you add credentials

## Hosted vs Self-hosted

The **Jentic hosted and VPC editions** offer deeper implementations across four areas:

| Capability            | Jentic Mini (this)                                                                                                                             | Jentic hosted / VPC                                                                                                                                                                     |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Search**            | BM25 full-text search                                                                                                                          | Advanced semantic search (~64% accuracy improvement over BM25)                                                                                                                          |
| **Request brokering** | In-process credential injection                                                                                                                | Scalable AWS Lambda-based broker with encryption at rest and in-transit, SOC 2-grade security, and 3rd-party credential vault integrations (HashiCorp Vault, AWS Secrets Manager, etc.) |
| **Simulation**        | Basic simulate mode                                                                                                                            | Full sandbox for simulating API calls and toolkit behaviour (enterprise-only)                                                                                                           |
| **Catalog**           | ~10,000+ APIs + ~380 workflow sources from [jentic-public-apis](https://github.com/jentic/jentic-public-apis); auto-imported on credential add | Central catalog — aggregates the collective know-how of agents across API definitions and Arazzo workflows                                                                              |

Jentic Mini is a self-hosted deployment option for individuals and small teams who want full control over their data and credentials. For teams that need managed scaling, SLAs, or enterprise features, [Jentic](https://jentic.com) offers hosted and on-premises editions — [get in touch](https://jentic.com/contact) to find out more.

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Quick Start (pre-built image)

**Hosting:** Host Jentic Mini separately from your agent where possible. Running both on the same machine gives the agent process direct access to the credential database, which weakens the security boundary.

From **DockerHub**:

```bash
docker run -d --name jentic-mini -p 8900:8900 -v jentic-mini-data:/app/data jentic/jentic-mini
```

From **GitHub Container Registry**:

```bash
docker run -d --name jentic-mini -p 8900:8900 -v jentic-mini-data:/app/data ghcr.io/jentic/jentic-mini
```

Open `http://localhost:8900` to complete setup.

### Quick Start (from source)

```bash
git clone https://github.com/jentic/jentic-mini.git
cd jentic-mini
docker compose up -d
```

Open `http://localhost:8900` to complete setup.

**Next:** Follow the [hands-on tutorial](docs/tutorials/01-notion-permissions.md) — connect the Notion API and see the permissions model in action.

### Configuration

Optional environment variables (set in `.env` or pass to `docker compose`):

| Variable                 | Default        | Description                                                                       |
| ------------------------ | -------------- | --------------------------------------------------------------------------------- |
| `JENTIC_VAULT_KEY`       | auto-generated | [Fernet](https://cryptography.io/en/latest/fernet/) key for the credentials vault |
| `JENTIC_PUBLIC_HOSTNAME` | `localhost`    | Public hostname for self-links and workflow IDs, e.g. `jentic.example.com`        |
| `LOG_LEVEL`              | `info`         | `debug`, `info`, `warning`, `error`                                               |

### Authentication

- **Toolkit key** (`tk_xxx`): scoped to a toolkit's credentials and policy — give this to agents
- **Human session**: username/password login for admin operations (credential management, toolkit setup)

First-time setup is guided through the UI at `http://localhost:8900`. Alternatively, via the API:

1. `POST /default-api-key/generate` from a trusted subnet to get your agent key
2. `POST /user/create` with `{"username": "...", "password": "..."}` to create an admin account
3. Add credentials for your APIs — specs are auto-imported from the [public catalog](https://github.com/jentic/jentic-public-apis)
4. Agents authenticate with the `tk_xxx` key via `X-Jentic-API-Key` header

## API Overview

| Tag             | Who uses it   | Purpose                                                                                   |
| --------------- | ------------- | ----------------------------------------------------------------------------------------- |
| **search**      | Agents        | Full-text search — the main entrypoint                                                    |
| **inspect**     | Agents        | Inspect a capability before calling it — parameters, response schema, auth requirements   |
| **execute**     | Agents        | Transparent request broker — runs API operations and Arazzo workflows                     |
| **toolkits**    | Agents/Humans | Toolkits, access keys, policies, permission requests                                      |
| **observe**     | Agents        | Read execution traces                                                                     |
| **catalog**     | Humans/admin  | Register APIs, browse public catalog, upload specs, overlays, notes                       |
| **credentials** | Humans only   | Manage the credentials vault; adding credentials auto-imports catalog specs and workflows |

## Public Catalog

Jentic Mini is connected to the [Jentic public API catalog](https://github.com/jentic/jentic-public-apis) — ~10,000+ API specs and ~380 Arazzo workflow sources.

The catalog manifest is fetched lazily at startup (two GitHub API calls) and cached locally for 24 hours. Specs and workflows are imported **automatically** the first time you add credentials for a catalog API.

```http
# Just add credentials — Jentic Mini handles the rest
POST /credentials
{ "api_id": "slack.com", "auth_type": "bearer", "value": "xoxb-..." }

# Slack's 17 workflows and its full API spec are now in your local registry
GET /workflows?source=local&q=slack
```

See [docs/catalog.md](https://github.com/jentic/jentic-mini/blob/main/docs/catalog.md) for full details.

## Updating

Pull the latest image from whichever registry you originally used, then recreate the container.

If you used `docker run` (replace the image name with `ghcr.io/jentic/jentic-mini` if you used GHCR):

```bash
docker pull jentic/jentic-mini:latest
docker stop jentic-mini && docker rm jentic-mini
docker run -d --name jentic-mini -p 8900:8900 -v jentic-mini-data:/app/data jentic/jentic-mini
```

If you used `docker compose`:

```bash
docker compose pull jentic-mini && docker compose up -d jentic-mini
```

Database migrations run automatically on startup, so your data is preserved across updates.

## Browser Requirements

The admin UI targets modern browsers: **Chrome 107+**, **Firefox 104+**, **Safari 16+**, **Edge 107+**.

## Development

Prerequisites for local development without Docker:

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 24](https://nodejs.org/) (matches Docker and `.nvmrc`)

Python source (`src/`) is volume-mounted into the container — edit any `.py` file and the server hot-reloads automatically.

For UI development, use the dev compose override which runs Vite in a container with full HMR:

```bash
docker compose -f compose.yml -f compose.dev.yml up
```

This starts a Vite dev server on `http://localhost:5173` with hot module replacement, proxying API calls to the backend on port 8900. Edit files in `ui/` and changes appear instantly. The Vite service uses the same `JENTIC_UID` / `JENTIC_GID` as `compose.yml` (defaults **1000:1000**), including for the bind-mounted `ui/` directory and for `npm`’s cache — **on Linux**, if your workstation user isn’t UID 1000, export matching values before spinning up compose (same snippet as below) so `./ui` is not littered with root- or mismatched-owner files from the container.

Alternatively, run Vite directly on the host (requires Node.js 24):

```bash
cd ui && npm install && npm run dev
```

### Testing

```bash
cd ui
npm run test:run       # Unit + integration tests (Vitest, browser mode)
npm run test:coverage  # With coverage report
npm run test:e2e       # Playwright E2E tests
```

See `ui/TESTING.md` for the full contributor guide.

To rebuild the production UI bundle: `cd ui && npm run build`, then `docker compose up -d --build`.

> **Note:** The backend container runs as a non-root user. `compose.yml` defaults to uid/gid 1000 for bind mount compatibility.
> If your host user has a different UID/GID (common on Linux), set `JENTIC_UID` and `JENTIC_GID` before starting — applies to **`compose.yml`** and to **`compose.dev.yml`** so the bundled Vite service matches too:
>
> ```bash
> JENTIC_UID=$(id -u) JENTIC_GID=$(id -g) docker compose up -d
> # or with UI dev server:
> JENTIC_UID=$(id -u) JENTIC_GID=$(id -g) docker compose -f compose.yml -f compose.dev.yml up
> ```

Swagger UI is available at `http://localhost:8900/docs` for interactive API exploration.

## Architecture

- **FastAPI + uvicorn** — async HTTP server with hot reload in dev
- **SQLite** — local registry, toolkit/key store, execution log
- **BM25** — in-memory full-text search index over operation descriptions
- **Fernet** — symmetric encryption for the credentials vault
- **arazzo-runner** — Arazzo workflow execution engine
- **@jentic/arazzo-ui** — React workflow visualization component (diagram/docs/split views) from [jentic-arazzo-tools](https://github.com/jentic/jentic-arazzo-tools)

## Telemetry & Community Contributions

On first startup, Jentic Mini generates a random UUID and registers it with Jentic (`https://api.jentic.com/api/v1/register-install`). This ID is fully anonymous — only the UUID is included in the registration payload, and no hostname or other machine identifiers are sent. As with any HTTPS request, the client IP address may still appear in standard server or network logs, but it is not included in the application payload.

This install ID is the foundation for community contribution features: when your instance discovers a working workflow or an API improvement, it can share that back under your anonymous install ID, benefiting everyone running Jentic. Disabling telemetry also disables the ability to contribute workflows and API fixes back to the community.

The install ID is stored locally at `/app/data/install-id.txt`. A second marker file (`/app/data/install-registered.txt`) is written after successful registration so that subsequent startups skip the network call.

**To opt out**, set `JENTIC_TELEMETRY=off`:

```bash
docker run -d --name jentic-mini -p 8900:8900 \
  -v jentic-mini-data:/app/data \
  -e JENTIC_TELEMETRY=off \
  jentic/jentic-mini
```

## Contributing

Please read our [Contributing Guide](https://github.com/jentic/.github/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/jentic/.github/blob/main/CODE_OF_CONDUCT.md) before submitting a pull request.

## License

This project is licensed under the [Apache 2.0 License](https://github.com/jentic/jentic-mini/blob/main/LICENSE).
