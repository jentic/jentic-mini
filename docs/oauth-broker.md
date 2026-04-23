# OAuthBroker Architecture

## Problem

OAuth-protected APIs require production app approval from the provider (Google, Slack, Salesforce, etc.) before you can handle OAuth flows on behalf of users. These approvals take months and require passing security reviews.

Jentic needs to call these APIs on behalf of users immediately, without waiting for approvals across hundreds of providers.

## Solution

Delegate OAuth to a provider that already has production approvals. **Pipedream Connect** has approvals for 3,000+ APIs and provides a transparent proxy: you send them the upstream URL + user identity, they inject the stored OAuth token server-side and forward verbatim.

This is a **temporary bridge**. When Jentic obtains its own OAuth app approvals, a `JenticOAuthBroker` replaces `PipedreamOAuthBroker` with zero changes to the broker layer or API surface.

## OAuthBroker Protocol

```python
class OAuthBroker(Protocol):
    async def covers(self, api_host: str, external_user_id: str) -> bool: ...
    async def get_token(self, api_host: str, external_user_id: str) -> str | None: ...
    async def proxy_request(self, api_host, upstream_path, method,
                             headers, body, query_string, external_user_id) -> httpx.Response | None: ...
```

Two modes:

| Mode | When | Mechanism |
|------|------|-----------|
| **Token** | Provider exposes raw token | `get_token()` returns Bearer token → broker injects and forwards normally |
| **Proxy** | Provider manages OAuth (no raw token) | `proxy_request()` rewrites URL and hands off entirely |

Pipedream managed OAuth = proxy mode. Jentic's future OAuth service = token mode.

## Request Flow

```
Agent: POST /api.slack.com/api/chat.postMessage
  │
  ▼
broker.py
  ├─ 1. Vault lookup: find credential for api.slack.com
  │     ↓ found → inject token, forward directly
  │     ↓ not found → try OAuthBroker registry
  │
  ├─ 2. OAuthBrokerRegistry.find_broker("slack.com", external_user_id)
  │     ↓ no broker covers this host → forward unauthenticated
  │     ↓ broker found →
  │
  ├─ 3a. broker.get_token() → token returned → inject, forward directly
  │
  └─ 3b. broker.get_token() → None (proxy mode) →
         broker.proxy_request() → Pipedream proxy → upstream API
```

`X-Jentic-External-User-Id` request header controls which user's connected accounts are used (default: `"default"`).

## Pipedream Connect Proxy

Proxy URL shape:
```
POST https://api.pipedream.com/v1/connect/{project_id}/proxy/{base64url(upstream_url)}
     ?external_user_id={id}&account_id={apn_xxx}
Authorization: Bearer {pipedream_access_token}
X-PD-Environment: production
```

- `upstream_url` = `https://{api_host}{path}?{query}` — full URL, base64url-encoded, no padding
- `account_id` = `apn_xxx` — Pipedream's identifier for the user's connected account
- Pipedream's access token = short-lived (1hr), obtained via client credentials flow, cached in memory
- Response is the raw upstream response — no wrapping

## DB Schema

```sql
-- Platform-level OAuth broker config (one row per registered broker)
CREATE TABLE oauth_brokers (
    id                       TEXT PRIMARY KEY,   -- e.g. "pipedream"
    type                     TEXT NOT NULL,       -- "pipedream"
    client_id                TEXT NOT NULL,
    client_secret_enc        TEXT NOT NULL,       -- Fernet-encrypted
    project_id               TEXT,
    environment              TEXT DEFAULT 'production',
    default_external_user_id TEXT DEFAULT 'default',
    created_at               REAL
);

-- Per-user, per-host connected account mappings
CREATE TABLE oauth_broker_accounts (
    id               TEXT PRIMARY KEY,
    broker_id        TEXT NOT NULL REFERENCES oauth_brokers(id) ON DELETE CASCADE,
    external_user_id TEXT NOT NULL,
    api_host         TEXT NOT NULL,   -- e.g. "api.slack.com"
    app_slug         TEXT NOT NULL,   -- e.g. "slack"
    account_id       TEXT NOT NULL,   -- e.g. "apn_abc123"
    healthy          INTEGER DEFAULT 1,
    synced_at        REAL,
    UNIQUE(broker_id, external_user_id, api_host)
);
```

## API Surface

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/oauth-brokers` | Register a broker (triggers discovery) |
| `GET` | `/oauth-brokers` | List all brokers |
| `GET` | `/oauth-brokers/{id}` | Get broker details |
| `GET` | `/oauth-brokers/{id}/accounts` | List discovered account mappings |
| `POST` | `/oauth-brokers/{id}/discover` | Re-run account discovery |
| `DELETE` | `/oauth-brokers/{id}` | Remove broker + all account mappings |

### Register a Pipedream broker

```json
POST /oauth-brokers
{
  "type": "pipedream",
  "client_id": "oa_abc123",
  "client_secret": "pd_secret_xxxx",
  "project_id": "proj_abc123",
  "environment": "production",
  "default_external_user_id": "default"
}
```

Response includes `accounts_discovered` — the count of API host mappings found for this project.

`client_secret` is write-only. Never returned.

## Account Discovery

On broker registration (and on `POST /oauth-brokers/{id}/discover`):

1. Fetch Pipedream access token via client credentials
2. `GET /accounts?external_user_id={id}` — list connected apps for this user
3. For each account, extract `app.name_slug` (e.g. `"slack"`)
4. Reverse-map slug → api_host(s) using the internal `API_ID_TO_PD_SLUG` mapping
5. Upsert into `oauth_broker_accounts`

When a user connects a new app via Pipedream's hosted OAuth UI, call
`POST /oauth-brokers/{id}/discover` to pull it in without re-registering.

## Migration Path: Pipedream → Jentic OAuth

When Jentic obtains its own OAuth app approvals for a provider:

1. Implement `JenticOAuthBroker` with `get_token()` returning a live bearer token
2. Register it alongside (or instead of) `PipedreamOAuthBroker`
3. The broker fallback chain picks it up automatically — zero changes elsewhere

The `OAuthBroker` protocol is the only interface the broker layer touches.

## Files

| File | Purpose |
|------|---------|
| `src/oauth_broker.py` | Protocol definition + `OAuthBrokerRegistry` singleton |
| `src/brokers/pipedream.py` | `PipedreamOAuthBroker` implementation |
| `src/routers/oauth_brokers.py` | CRUD API for managing broker configs |
| `src/routers/broker.py` | Vault-first fallback chain (modified) |
| `src/db.py` | `oauth_brokers` + `oauth_broker_accounts` tables |
