# Jentic Personal Edition (JPE)

Jentic Personal Edition is a locally-running proof-of-concept implementation of the Jentic API — built by Sean Blanchfield (CEO of Jentic) as an internal pressure artifact to validate the v2 API design and show the engineering team what a competitor could build quickly.

**This is NOT production Jentic.** It is a FastAPI + SQLite + uvicorn local service.

## Goals

1. Prove the API design works end-to-end
2. Test real agent workflows against real APIs
3. Demonstrate execution speed
4. Act as a living specification for the real Jentic platform

## Quick Start

```bash
# From the host config directory
cd /configs/jentic-personal-edition
docker compose up -d
```

- Service: http://localhost:8900
- Swagger UI: http://localhost:8900/docs
- Redoc: http://localhost:8900/redoc
- Public URL (home network): https://localhost

Authenticate all requests with the `X-Jentic-API-Key` header.

## Environment Variables

Set in `/configs/jentic-personal-edition/docker-compose.yml`:

| Variable | Purpose | Default |
|---|---|---|
| `JENTIC_VAULT_KEY` | Fernet key for credential encryption | Auto-generated to `data/vault.key` if absent/invalid |
| `DB_PATH` | SQLite database path | `/app/data/jpe.db` |
| `JENTIC_PUBLIC_HOSTNAME` | Public hostname for workflow capability IDs | `localhost` |

## File Layout

```
/mnt/jentic-pe/              ← host mount point (= /app/ inside container)
  src/                       ← Python source (uvicorn hot-reloads this)
    main.py                  ← FastAPI app, router registration, OpenAPI schema
    auth.py                  ← API key middleware
    db.py                    ← SQLite schema + migrations
    vault.py                 ← Fernet-encrypted credential store
    bm25.py                  ← In-memory BM25 search index
    models.py                ← Pydantic request/response models
    utils.py                 ← Shared helpers (_abbreviate, vendor extraction, etc.)
    routers/
      capability.py          ← GET /inspect/{id}
      search.py              ← GET /search
      apis.py                ← GET /apis/... (+ hidden POST /apis)
      workflows.py           ← GET /workflows/..., workflow dispatch
      broker.py              ← catch-all /{host}/{path} proxy
      import_.py             ← POST /import
      overlays.py            ← POST /apis/{id}/scheme, /overlays
      credentials.py         ← /credentials
      collections.py         ← /collections/...
      permissions.py         ← /permission-requests
      notes.py               ← /notes
      traces.py              ← /traces/...
      debug.py               ← /debug/... (hidden from OpenAPI schema)
    static/                  ← Swagger UI + Redoc assets (no CDN, works offline)
    specs/                   ← Downloaded OpenAPI spec files + Arazzo workflows
  data/                      ← SQLite DB + vault.key (Docker volume, NOT in git)
  docs/                      ← This documentation
```

## Current API Corpus

26 APIs, ~5,200 operations registered:

`api.github.com` · `slack.com/api` · `api.stripe.com` · `api.twilio.com` · `api.openai.com` · `api.hubapi.com` · `api.sendgrid.com` · `api.elevenlabs.io` · `app.asana.com/api` · `atlassian.net` · `discord.com/api` · `travelpartner.googleapis.com` · `api.mailchimp.com` · `api.spotify.com` · `api.telegram.org` · `trello.com` · `api.twitter.com` · `api.zoom.us` · `api.anthropic.com` · `huggingface.co` · `api.mistral.ai` · `api.intercom.io` · `broker-api.alpaca.markets` · `api.apollo.io/api` · `gitlab.com/api` · `techpreneurs.ie`

## Key Concepts

- **Capability ID**: `METHOD/host/path` — e.g. `GET/api.elevenlabs.io/v1/voices`
- **Workflow ID**: `POST/localhost/workflows/slug`
- **Collection**: a named bundle of credentials with its own API key(s), policies, and IP restrictions
- **Broker**: the catch-all proxy at `/{host}/{path}` that injects credentials and enforces policy
- **Overlay**: a client-contributed security scheme patch for APIs with broken/missing auth specs

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, component map, database schema
- [CREDENTIALS.md](CREDENTIALS.md) — vault, credential lifecycle, auth flywheel
- [WORKFLOWS.md](WORKFLOWS.md) — Arazzo workflows, execution model, examples
- [DEVELOPMENT.md](DEVELOPMENT.md) — dev workflow, adding APIs, Docker layout, debugging
- [ROADMAP.md](ROADMAP.md) — what's built, what's next
