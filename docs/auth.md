# Authentication & Authorisation

## Overview

Jentic Mini uses two distinct authentication mechanisms for two distinct actors:

| Actor | Mechanism | Purpose |
|---|---|---|
| **Human** | bcrypt password → httpOnly JWT cookie | Admin operations, approving permission requests, managing keys |
| **Agent** | `X-Jentic-API-Key: tk_xxx` | Search, inspect, execute, toolkit-scoped operations |

There is **no admin API key** (no `JENTIC_API_KEY` env var). CLI access to the container is
already a stronger trust boundary — anyone with `docker exec` can read the database directly.
Adding a secret env var on top creates a credential that can be leaked without adding security.

---

## Human Authentication

### Account model

Single root account — no multi-user, no roles. One human owns the instance.

**Account creation is one-time.** `POST /user/create` returns `410 Gone` after the first call.

### Endpoints

| Method | Path | Auth required | Notes |
|---|---|---|---|
| `POST` | `/user/create` | None (one-time) | Creates root account and issues session cookie (auto-login). 410 after first call. |
| `POST` | `/user/login` | None | Returns httpOnly JWT cookie on success. |
| `POST` | `/user/token` | None | OAuth2 password grant for Swagger UI; returns Bearer JWT. |
| `POST` | `/user/logout` | Human session | Clears cookie. |
| `GET` | `/user/me` | Optional | Returns current auth/session context; works with no auth. |

**Password reset is CLI-only.** No "forgot password" link, no email reset, no security
questions. If the password is lost, run:

```bash
docker exec -it jentic-mini python3 -m src reset-password
```

The CLI prompts twice (with confirmation), enforces the same 8-character minimum as
`POST /user/create`, and rewrites `users.password_hash` in place. To start over with
one-time `POST /user/create` instead (e.g. to change the username), drop the `users`
row and clear the `account_created` setting via direct SQLite edit. `docker exec` is
deliberately the only superuser path (see Overview).

### JWT

- Algorithm: `HS256`, secret generated at first startup and stored in the settings table
- Expiry: **30-day sliding window** — token expires 30 days after last use
- Rolling: on every authenticated request, if the token is older than 1 day, a fresh 30-day token is issued via `Set-Cookie` on the response
- Storage: httpOnly, SameSite=Strict cookie — not accessible to JavaScript
- Effect: the human stays logged in indefinitely as long as they use the UI within any 30-day window

### What currently requires a human session

Human-session-only enforcement is applied per-route (via `Depends(require_human_session)`) on
sensitive endpoints. Key examples:

- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/approve`
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/deny`
- `PATCH /toolkits/{toolkit_id}`
- `DELETE /toolkits/{toolkit_id}`
- `PUT|PATCH /toolkits/{toolkit_id}/credentials/{cred_id}/permissions`
- `POST|PATCH|DELETE /oauth-brokers...` admin endpoints

`POST /default-api-key/generate` also requires a human session **after** first claim.

Not all write operations are currently human-session-only: some routes allow agent keys when
policy allows (for example credential writes with explicit credential policy rules).

---

## Agent Authentication

### Key format

All agent keys use the prefix `tk_` (toolkit key) followed by 32 hex characters
(`secrets.token_hex(16)`). Example: `tk_a1b2c3d4e5f67890abcdef1234567890abcd`.

Keys are passed via header:
```
X-Jentic-API-Key: tk_a1b2c3d4e5f67890abcdef1234567890abcd
```

### Default API key

Every instance has exactly one **default API key**, bound to the default toolkit. This is the
key issued to an agent during self-enrollment (see below).

The default key is bound to the `default` toolkit and can be used immediately for normal
agent flows (search/inspect/execute and toolkit-scoped operations).

### Additional keys

Additional `tk_xxx` keys can be issued per toolkit. Keys are individually revocable and support
per-key IP restrictions (`allowed_ips` CIDR list).

New keys are **never issued unrestricted**: if no explicit allowlist is supplied, `allowed_ips`
defaults to the trusted-subnets list (RFC-1918 + loopback + any `JENTIC_TRUSTED_SUBNETS` extras).
A key row with `NULL` or empty `allowed_ips` is still evaluated against the trusted-subnets list
at request time — subnet is the perimeter, not the absence of restriction.

### Scopes (planned)

Fine-grained scope assignment is planned (`api_keys` table). Current implementation is primarily
toolkit identity + route-level human-session guards + credential policy checks.

---

## Unauthenticated Access

Some endpoints are intentionally open — no key required:

| Path | Reason |
|---|---|
| `GET /health` | Discovery; explicit setup instructions for agents |
| `POST /default-api-key/generate` | Self-enrollment (subnet-only on first call) |
| `POST /user/create`, `POST /user/login`, `POST /user/token` | Initial/setup and human login flows |
| `GET /user/me` | Session/auth context probe (works with or without auth) |
| `GET /docs`, `/redoc`, `/openapi.json` | API documentation |
| `GET /static/*` | Static assets |
| `/{host}/{path}` (broker) | Transparent conduit — upstream auth is upstream's problem |
| `POST /workflows/{slug}` | Open passthrough workflow execution |

**Broker and workflow execution with no key:** `request.state.toolkit_id = None`. The broker
skips credential injection and policy enforcement, then forwards the request clean. If the
upstream API requires auth and no credentials are present, the upstream returns 401/403, which
the broker passes through unmodified. Jentic Mini does not gate access to third-party APIs that
don't require credentials.

**Search, inspect, catalog** currently require a key. Public catalog visibility (returning only
`public: true` results to unauthenticated callers) is a separate future design — see the main
design document.

---

## Self-Enrollment Flow

The intended zero-human-intervention onboarding path for an agent:

### 1. Discovery

```
GET /health
→ 200 {"status": "setup_required",
        "message": "No default API key has been issued yet.",
        "next_step": "Call POST /default-api-key/generate from a trusted subnet to obtain your agent key.",
        "generate_url": "/default-api-key/generate"}
```

### 2. Key claim

```
POST /default-api-key/generate   (no auth, subnet IP only)
→ 201 {"key": "tk_a1b2c3d4e5f67890abcdef1234567890abcd",
        "message": "This key will not be shown again. Store it securely.",
        "next_step": "Tell your user to visit setup_url to create their admin account.",
        "setup_url": "https://jentic-mini.example.com/user/create"}
```

The key is **returned once only by this endpoint**, but it is stored in `toolkit_keys.api_key`
for runtime lookup (i.e., anyone with direct database access can read it). If lost at the API/UI
layer, regenerate it.

After this call, `POST /default-api-key/generate` requires a human session on all subsequent
calls.

### 3. Health check confirms key is active

```
GET /health
→ 200 {"status": "account_required",
        "message": "Agent key is active. No admin account has been created yet.",
        "next_step": "Tell your user to visit setup_url to create their admin account.",
        "setup_url": "https://jentic-mini.example.com/user/create"}
```

The agent key works immediately — the agent does not need to wait for the human to complete
account setup before executing broker calls or workflows.

### 4. Human creates root account (separate, async)

The agent tells its human to visit `setup_url`. Human sets username and password. `POST /user/create` closes permanently.

```
GET /health
→ 200 {"status": "ok", "version": "...", "apis_registered": 23}
```

### Race condition / human-first variant

The human may visit the UI before the agent has connected. The UI's first-run screen shows:

> **Your default agent key is: `tk_a1b2c3d4e5f67890abcdef1234567890abcd`**
> Copy this into your agent configuration. It will not be shown again.

Under the hood this is the same `POST /default-api-key/generate` call — just surfaced in the
UI rather than via API. Whoever calls the endpoint first (agent or human) claims the key.

### Subnet restriction

`POST /default-api-key/generate` (unauthenticated, first-call only) is restricted to trusted
subnets. Default allowed ranges:
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `127.0.0.0/8`
- `::1/128`

Extended via `JENTIC_TRUSTED_SUBNETS` env var (comma-separated CIDR list). The env var
**appends** to the built-in defaults — setting it never removes the RFC-1918/loopback entries.
This prevents an internet-facing instance from being claimed by an attacker before the
legitimate agent.

---

## Key Regeneration (Rescue)

If the agent loses its key:

1. Human logs into UI → **Keys** section → **Regenerate default key**
2. Old key is revoked (soft delete via `revoked_at`)
3. New `tk_xxx` key is issued and shown once
4. Human copies it into agent configuration

The UI also supports issuing an *additional* key without revoking the old one — useful if the
agent is mid-task and you don't want to interrupt it.

---

## Threat Model

**Primary concern: prompt injection causing destructive writes.**

Concrete attack chain (now mitigated):
1. Attacker injects prompt into data the agent processes (e.g. an email)
2. Agent is instructed to elevate its own Gmail credential access
3. Agent calls `POST /toolkits/{toolkit_id}/access-requests` requesting a grant/permission change
4. Without mitigation: agent could approve its own escalation request
5. Agent forwards emails to attacker's address

**Mitigation:** `approve` / `deny` are human-session-only:
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/approve`
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/deny`

An agent key cannot call these routes. The human approves via the `/approve/{toolkit_id}/{req_id}` UI flow with a valid JWT session.

**Secondary concern: leaked agent key used by a third party.**

Mitigated by per-key IP restriction (CIDR allowlist on `toolkit_keys` row). Recommended: set
`JENTIC_TRUSTED_SUBNETS` and configure key IP restrictions to local subnets only.

---

## Database tables (auth-related)

### `users`

Single root account.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `username` | TEXT UNIQUE | |
| `password_hash` | TEXT | bcrypt |
| `created_at` | TIMESTAMP | |

### `settings`

Key-value store for instance configuration.

| Key | Value |
|---|---|
| `jwt_secret` | Random 32-byte hex, generated at first startup |
| `default_key_claimed` | `1` after first `POST /default-api-key/generate` |
| `account_created` | `1` after first `POST /user/create` |

### `toolkit_keys`

One row per issued agent key. For conceptual model see `docs/architecture.md`; for exact schema
and current columns see Alembic migrations in `alembic/versions/`.

Key columns in current schema: `api_key` (the `tk_xxx` string), `toolkit_id`, `allowed_ips`, `revoked_at`, `created_at`.
Planned scopes are tracked separately via `api_keys` (not yet active for toolkit key enforcement).

---

## Runtime dependencies (current)

Auth currently uses:

- `bcrypt`
- `python-jose[cryptography]`

These are declared in `pyproject.toml`.
