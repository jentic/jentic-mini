# Authentication & Authorisation

## Overview

Jentic Mini uses two distinct authentication mechanisms for two distinct actors:

| Actor | Mechanism | Purpose |
|---|---|---|
| **Human** | bcrypt password → httpOnly JWT cookie | Admin operations, approving permission requests, managing keys |
| **Agent** | `tk_xxx` bearer key header | Search, inspect, execute, toolkit-scoped operations |

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
| `POST` | `/user/create` | None (one-time) | Creates root account. 410 after first call. |
| `POST` | `/user/login` | None | Returns httpOnly JWT cookie on success. |
| `POST` | `/user/logout` | Human session | Clears cookie. |

**Password reset is CLI-only:**
```bash
docker exec jentic-mini python3 -m jentic reset-password
```
No "forgot password" link. No email. No security questions.

### JWT

- Algorithm: `HS256`, secret generated at first startup and stored in the settings table
- Expiry: **30-day sliding window** — token expires 30 days after last use
- Rolling: on every authenticated request, if the token is older than 1 day, a fresh 30-day token is issued via `Set-Cookie` on the response
- Storage: httpOnly, SameSite=Strict cookie — not accessible to JavaScript
- Effect: the human stays logged in indefinitely as long as they use the UI within any 30-day window

### What requires a human session

Any operation that cannot safely be delegated to an automated process:

- Create, update, delete toolkits
- Create, update, delete upstream API credentials
- **Approve or deny permission requests** — never callable with an agent key, period
- Regenerate the default API key (after first issue)
- `/user/create`, `/user/logout`

This is enforced in the auth middleware: endpoints in the "human session only" set check
`request.state.is_human_session` and return `403` if called with an agent key, regardless of
the key's scopes. An agent cannot self-approve its own permission escalation requests.

---

## Agent Authentication

### Key format

All agent keys use the prefix `tk_` (toolkit key). Example: `tk_a1b2c3d4e5f6`.

Keys are passed via header:
```
X-Jentic-API-Key: tk_a1b2c3d4e5f6
```

### Default API key

Every instance has exactly one **default API key**, bound to the default toolkit. This is the
key issued to an agent during self-enrollment (see below).

The default key has a sensible default scope:
- ✅ Execute (broker proxy)
- ✅ Search, inspect catalog
- ✅ Read toolkit metadata
- ✅ Submit permission requests
- ❌ Write credentials, toolkits, policies
- ❌ Approve permission requests (human session only — always)

### Additional keys

The human can issue additional `tk_xxx` keys via the UI (bound to any toolkit, with any scope
the human chooses). Keys are individually revocable. Per-key IP restrictions (CIDR list) are
supported.

### Scopes (planned)

Fine-grained scope assignment is planned (`api_keys` table in schema). Current implementation
uses `is_admin` boolean; this will be replaced with a scope set stored on the key row.

---

## Unauthenticated Access

Some endpoints are intentionally open — no key required:

| Path | Reason |
|---|---|
| `GET /health` | Discovery; explicit setup instructions for agents |
| `POST /default-api-key/generate` | Self-enrollment (subnet-only on first call) |
| `GET /docs`, `/redoc`, `/openapi.json` | API documentation |
| `GET /static/*` | Static assets |
| `/{host}/{path}` (broker) | Transparent conduit — upstream auth is upstream's problem |
| Workflow execution | Same as broker |

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
→ 201 {"key": "tk_a1b2c3d4e5f6",
        "message": "This key will not be shown again. Store it securely.",
        "next_step": "Tell your user to visit setup_url to create their admin account.",
        "setup_url": "https://jentic-mini.example.com/user/create"}
```

The key is **returned once only**. It is stored as a bcrypt hash — the plaintext is not
recoverable. If lost, the human regenerates it via the UI.

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

> **Your default agent key is: `tk_a1b2c3d4e5f6`**
> Copy this into your agent configuration. It will not be shown again.

Under the hood this is the same `POST /default-api-key/generate` call — just surfaced in the
UI rather than via API. Whoever calls the endpoint first (agent or human) claims the key.

### Subnet restriction

`POST /default-api-key/generate` (unauthenticated, first-call only) is restricted to trusted
subnets. Default allowed ranges:
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `127.0.0.1/32`

Configurable via `JENTIC_TRUSTED_SUBNETS` env var (comma-separated CIDR list). This prevents
an internet-facing instance from being claimed by an attacker before the legitimate agent.

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
3. Agent calls `POST /permission-requests` requesting `add_scope` for Gmail
4. Without mitigation: agent calls `POST /permission-requests/{id}/resolve` with `status: approved` — privileges elevated without human knowledge
5. Agent forwards emails to attacker's address

**Mitigation:** `resolve` is `human_session_only`. An agent key — regardless of scope — cannot
call it. The human must physically approve at the `/approve/{id}` UI page, which requires a
valid JWT cookie.

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

One row per issued agent key. See main schema in ARCHITECTURE.md.

Key columns: `api_key` (the `tk_xxx` string), `toolkit_id`, `allowed_ips`, `revoked_at`, `scopes` (JSON array — planned).

---

## Dependencies

New packages required (add to `requirements.txt` / Dockerfile):

```
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
```
