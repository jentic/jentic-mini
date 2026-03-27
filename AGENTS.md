# AGENTS.md — Jentic Mini Agent Onboarding

This document tells AI agents how to use a Jentic Mini instance. For the full
skill integration guide, see <https://clawhub.ai/skills/jentic>.

## What is Jentic Mini?

Jentic Mini is a self-hosted API middleware for AI agents. It lets you
**search** for APIs, **inspect** their schemas, and **execute** requests
through a broker that injects credentials on your behalf.

**Credentials live in Jentic, not in the agent.** API secrets are stored
and managed in the broker — agents never see or handle them directly.
This eliminates prompt injection risks from embedded API keys.

### Two-actor trust boundary

| Actor | Auth method | Capabilities |
|-------|-------------|--------------|
| Agent | `X-Jentic-API-Key: tk_xxx` | Search, inspect, execute, request permissions |
| Human | Username + password (UI session) | Approve requests, manage credentials, OAuth flows |

## Getting Started

### 1. Human: Create an admin account

Open `/setup` in a browser on this Jentic Mini instance and create an admin account
(username + password). This account is used for human-only operations
like approving access requests and managing credentials.

### 2. Agent: Claim your API key

Check instance health and claim the default agent key:

```
GET /health
→ {"status": "setup_required", ...}

POST /default-api-key/generate
→ {"key": "tk_xxx", "toolkit_id": "default", ...}
```

The key is shown **once only** — store it securely. If the human has
already generated the key via the setup UI, they will provide it to you.

### 3. Start using the API

Set the key on all subsequent requests:

```
X-Jentic-API-Key: tk_xxx
```

Then follow the Search, Inspect, Execute workflow below.

## Authentication

Include your toolkit key on every request:

```
X-Jentic-API-Key: tk_xxx
```

Key public endpoints that do not require a key: `/health`, `/docs`,
`/openapi.json`, `/llms.txt`.

## Core Workflow: Search, Inspect, Execute

### 1. Search

Find APIs and workflows by intent:

```
GET /search?q=send+email&n=5
```

Returns ranked results with capability IDs and links.

### 2. Inspect

Get the full schema for a capability before calling it:

```
GET /inspect/POST%2Fapi.sendgrid.com%2Fv3%2Fmail%2Fsend
```

Returns parameters, response schema, auth requirements, error taxonomy, and
an `_links.execute` URL. Supports `Accept: text/markdown` for an LLM-friendly
format.

**Capability ID format:** `METHOD/host/path` (e.g., `GET/api.stripe.com/v1/customers`).

### 3. Execute

Call the API through the broker. The broker injects credentials automatically:

```
POST /api.sendgrid.com/v3/mail/send
X-Jentic-API-Key: tk_xxx
Content-Type: application/json

{"personalizations": [{"to": [{"email": "user@example.com"}]}], ...}
```

The broker resolves your toolkit, finds the matching credential, injects the
auth header, forwards to the upstream API, logs a trace, and returns the
response verbatim.

## Workflow Execution

Multi-step workflows (Arazzo specs) are executed the same way:

```
POST /workflows/summarise-discourse-topics
X-Jentic-API-Key: tk_xxx
Content-Type: application/json

{"forum_url": "discourse.example.com", "topic_count": 5}
```

Each step in the workflow routes through the broker, so every upstream call
gets credential injection and tracing.

## Async Execution

Use `Prefer: wait=0` to get an immediate 202 with a job ID:

```
POST /api.stripe.com/v1/charges
Prefer: wait=0
X-Jentic-API-Key: tk_xxx
```

Poll `GET /jobs/{job_id}` until status is `complete` or `failed`.

## Permission Escalation

If a request is denied by policy (403), request expanded permissions:

```
POST /toolkits/{toolkit_id}/access-requests
X-Jentic-API-Key: tk_xxx
Content-Type: application/json

{
  "type": "modify_permissions",
  "credential_id": "slack-bot",
  "rules": [{"effect": "allow", "methods": ["POST"], "path": "chat.postMessage"}],
  "reason": "Need to send messages to Slack channels"
}
```

A human approves the request, then retry the original call.

## Observability

- `GET /traces` — list recent execution traces
- `GET /traces/{trace_id}` — full trace detail (timing, status, step outputs)

## API Reference

Interactive docs at `/docs` (Swagger UI) and `/redoc`. Machine-readable
OpenAPI spec at `/openapi.json`.

## Key Endpoints Summary

| Action | Endpoint |
|--------|----------|
| Bootstrap | `GET /health` |
| Search | `GET /search?q=TEXT` |
| Inspect | `GET /inspect/{capability_id}` |
| Execute | `{METHOD} /{upstream_host}/{path}` |
| Workflows | `GET /workflows`, `POST /workflows/{slug}` |
| Traces | `GET /traces`, `GET /traces/{trace_id}` |
| Async jobs | `GET /jobs/{job_id}` |
| Catalog | `GET /apis`, `GET /catalog` |
| Escalation | `POST /toolkits/{id}/access-requests` |

## Credential Injection

Credentials are **never** exposed to agents. The broker:

1. Identifies the upstream API from the request URL
2. Looks up credentials bound to your toolkit for that API
3. Reads the security scheme from the spec (+ overlays)
4. Injects the auth header (Bearer, Basic, or apiKey)
5. Forwards to the upstream API
6. Logs a trace

If no credentials are configured for an API, the broker returns
`CREDENTIAL_LOOKUP_FAILED` with instructions to request access.
