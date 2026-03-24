# Roadmap

## Completed — Session 2026-03-15

Everything listed here was built in a single session as a proof-of-concept implementation.

### Core Infrastructure

- FastAPI + SQLite service on port 8900 with uvicorn hot reload
- Docker Compose deployment at `/configs/jentic-personal-edition/`
- Fernet-encrypted credential vault (write-only semantics)
- Swagger UI + Redoc served locally from vendored assets (no CDN dependency)
- Public URL via Caddy reverse proxy: https://localhost

### Catalog

- `GET /search` — BM25 full-text search over 26 APIs / ~5,200 operations + registered workflows
- `GET /inspect/{id}` — unified capability inspection for operations and workflows
- `GET /apis/...` — list and get registered APIs with pagination
- `GET /workflows/...` — list and get registered workflows
- `POST /import` — register APIs (URL/file/inline) and Arazzo workflows
- Capability IDs: `METHOD/host/path` format (no scheme, no spaces)
- Description abbreviation (≤3 sentences) for token efficiency in LLM consumers
- Vendor name extraction from API ID
- HATEOAS `_links` on all paginated and resource responses

### Execution

- Transparent broker proxy: `/{host}/{path}` (catch-all, registered last)
- Automatic credential injection: API key header, bearer, basic, multiple headers
- Simulate mode: `X-Jentic-Simulate: true` — returns mock 200 without calling upstream
- Policy enforcement: allow/deny rules per collection, first-match-wins
- Arazzo workflow execution via vendored arazzo-runner fork
- All workflow steps route through the broker (single credential injection chokepoint)
- Workflow broker dispatch: `POST /{jpe_host}/workflows/{slug}` routes internally without external HTTP hop
- Execution traces: step-level data stored in SQLite (`executions` + `execution_steps`)
- Workflow error propagation: returns upstream HTTP status, `failed_step` detail, remediation hints

### Access Control

- Collections: scoped credential bundles (global credentials, collection-scoped binding)
- Multi-key collections: one key per agent, individually revocable
- Per-key IP restrictions: CIDR array evaluated at request time
- Collection policies: allow/deny rules per collection with first-match-wins evaluation
- Permission requests: agents can request access they don't have; humans approve/deny

### Auth Flywheel

- Security scheme overlays: `POST /apis/{id}/scheme` registers pending overlay
- Auto-confirmation: on first successful broker 2xx, overlay flips to confirmed
- Handles APIs with missing/incorrect security schemes in their OpenAPI specs (Discourse pattern)
- Raw overlay registration: `POST /apis/{id}/overlays` for full control

### API Design

- Tag taxonomy: discover → execute → observe → collections → permissions → credentials → catalog
- Swagger UI tag ordering via `openapi_tags` in `main.py`
- Agent-oriented endpoint summaries: active voice, intent-matching up front
- Broker shortcut (`/workflows/{slug}`) hidden; broker path is canonical for consistency

---

## Known Gaps and Next Priorities

### High Priority

**Step-to-step data transformation**
Arazzo runtime expressions (`$steps.X.outputs.Y`) pass data verbatim. When step 1 returns a large response (e.g. 500KB Discourse topics list) and step 2 is a token-limited API (OpenAI), the workflow fails with a 400.

Options:
- Custom Arazzo extension: a `transform` step type with jq/JSONPath filter
- JPE pseudo-operation: `POST /localhost/transform` that accepts `{data, filter}` and returns filtered result — agents can include this as a workflow step
- Input preprocessing: let callers pre-filter before invoking the workflow (workaround, not a fix)

**Async workflow execution**
Long-running workflows block the HTTP response indefinitely. Need:
- `Prefer: wait=N` header support (RFC 7240): return a job ID if execution exceeds N seconds
- `GET /executions/{id}/status` polling endpoint
- Possibly: Server-Sent Events for live step progress

**Complex multi-API workflow testing**
The broker-based Arazzo execution path (server URL rewriting + RuntimeParams) needs more testing with workflows that span multiple APIs with different auth schemes. Current test coverage: Techpreneurs (no auth) + OpenAI (bearer).

### Medium Priority

**Unauthenticated search**
Currently all endpoints require an API key. For cold-start / agent discovery without a key:
- Rate-limited `GET /search` without authentication
- Returns capability IDs and summaries only (no execute links until authenticated)
- Would enable agents to self-bootstrap without a pre-configured key

**Credential provisioning flow (human-in-the-loop)**
Current model: agent stores credentials directly via `POST /credentials`. This means the agent must hold the plaintext value — a security concern.

Better model:
1. Agent calls `POST /credentials/provision` with label + api_id (no value)
2. JPE generates a `user_url` where the human can enter the value directly
3. Agent polls `GET /credentials/{id}/status` until `provisioned`
4. Agent never sees the plaintext value

**Schema samples**
`POST /samples` endpoint: given an operation/workflow ID, return example request bodies and response shapes. Useful for simulate mode grounding (agents can see realistic mock data structures).

**llms.txt**
Standard `GET /llms.txt` endpoint for LLM discovery. Returns a structured description of what JPE provides and how to use it. Follows emerging convention from llmstxt.org.

**Agent-contributed catalog (workflow authorship flywheel)**
- Agents can submit workflows via `POST /import` — initially private to their collection
- Workflow can be "promoted" to public by admin
- Enables a community catalog of tested workflows
- Same flywheel model as auth overlays

**Collection capability summary**
`GET /collections/{id}/summary` — LLM-generated prose description of what a collection can do (which APIs are credentialed, what policies allow, what workflows are accessible). Reduces the need for agents to enumerate all capabilities manually.

### Low Priority / Design Decisions Pending

**Async transport**
WebSocket vs long-polling for async workflow progress. Leaning toward SSE (Server-Sent Events) for simplicity, but needs a decision before implementation.

**Production workflow domain**
Workflow IDs currently use `localhost:8900`. Production Jentic needs a canonical domain. Options: `jentic.net`, `functioncall.net`. Decision pending.

**OAuth2 bundled setup flow**
OAuth2 APIs (Spotify, Google, Slack user tokens, etc.) require multi-step human interaction for initial token grant. Proposed: agent calls `POST /credentials/oauth2/init`, JPE returns a single URL where the human completes the OAuth dance, JPE stores the access + refresh tokens, handles refresh automatically. Agent never touches the OAuth flow.

**Workflow step-level credential injection**
Currently credentials are injected at the collection level — the same credential is used for all steps that hit the same API. Some workflows may need different credentials for the same API host in different steps. Would require step-level credential overrides in the Arazzo spec or a JPE extension.

**HMAC request signing**
For higher-assurance credential binding: sign each broker request with an HMAC derived from the credential, verifiable at the upstream API without transmitting the raw key. Relevant for APIs that support request signing (AWS, Stripe webhook validation, etc.).

**Pagination model review**
All paginated endpoints currently use integer page numbers. Need to confirm: is cursor-based pagination ever needed for the APIs JPE proxies, or is page-number sufficient for the catalog/search use cases?

---

## Design Doc References

The authoritative v2 API design (what JPE is implementing) lives at:

- `/root/.openclaw/workspace/docs/jentic/jentic-api-design/shirka-v2-proposal.md`
- `/root/.openclaw/workspace/docs/jentic/jentic-api-design/requirements.md`

When in doubt about intended behaviour, read these first. JPE is the proof; these docs are the spec.
