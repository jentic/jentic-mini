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

The authoritative schema lives in `alembic/versions/` — see `0001_baseline.py` and
subsequent revisions (`0002`, `0003` amend the OAuth-broker tables). The tables
in play:

- **`oauth_brokers`** — one row per registered broker: `id`, `type`, `client_id`,
  `client_secret_enc` (Fernet-encrypted), `project_id`, `environment`,
  `default_external_user_id`, `created_at`.
- **`oauth_broker_accounts`** — per-user, per-host connected account mappings:
  `id`, `broker_id`, `external_user_id`, `api_host`, `app_slug`, `account_id`
  (e.g. `apn_xxx`), `label`, `api_id`, `healthy`, `synced_at`. The effective
  uniqueness is `(broker_id, external_user_id, api_host, account_id)` after
  migration `0002` — multiple accounts per host per user are allowed.
- **`oauth_broker_connect_labels`** — labels pinned to outstanding connect-link
  flows so that the sync step can name the resulting credential correctly.
- **`api_broker_apps`** — mapping of `api_id` → `broker_app_id` seeded at startup
  from `API_ID_TO_PD_SLUG` (see `src/brokers/pipedream.py`) for each registered
  broker.

## API Surface

All routes are mounted under `/oauth-brokers`. `{broker_id}` is the registered
broker's ID (`pipedream` by default when you register a single Pipedream broker).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/oauth-brokers` | Human session | Register a broker |
| `GET` | `/oauth-brokers` | Any key | List registered brokers |
| `GET` | `/oauth-brokers/{broker_id}` | Any key | Get broker details |
| `PATCH` | `/oauth-brokers/{broker_id}` | Human session | Update broker config |
| `DELETE` | `/oauth-brokers/{broker_id}` | Human session | Remove broker + all account mappings |
| `POST` | `/oauth-brokers/{broker_id}/connect-link` | Agent or human | Generate a one-time OAuth connect URL |
| `POST` | `/oauth-brokers/{broker_id}/sync` | Agent or human | Sync connected accounts into the vault, triggering discovery |
| `GET` | `/oauth-brokers/{broker_id}/accounts` | Any key | List discovered account mappings |
| `PATCH` | `/oauth-brokers/{broker_id}/accounts/{account_id}` | Human session | Update account metadata (label) |
| `DELETE` | `/oauth-brokers/{broker_id}/accounts/{account_id}` | Human session | Disconnect an account (revoke + local cleanup) |
| `POST` | `/oauth-brokers/{broker_id}/accounts/{account_id}/reconnect-link` | Human session | Get a reconnect link for an existing account |

### Register a Pipedream broker

```json
POST /oauth-brokers
{
  "type": "pipedream",
  "config": {
    "client_id": "oa_abc123",
    "client_secret": "pd_secret_xxxx",
    "project_id": "proj_abc123",
    "environment": "production",
    "support_email": "admin@example.com"
  }
}
```

Response (`OAuthBrokerOut`) echoes the broker's `id`, `type`, non-sensitive `config`, `created_at`, and an `accounts_discovered` count (populated by an initial `discover_accounts("default")` call made on registration).

`client_secret` is write-only — never returned via the API.

## Account Discovery

Discovery runs inside `POST /oauth-brokers/{broker_id}/sync`:

1. Fetch Pipedream access token via client credentials
2. `GET /accounts?external_user_id={id}` — list connected apps for this user
3. For each account, extract `app.name_slug` (or fall back to `app.slug` when missing) — e.g. `"slack"`
4. Reverse-map slug → api_host(s) using the internal `API_ID_TO_PD_SLUG` mapping (see `src/brokers/pipedream.py`)
5. Upsert into `oauth_broker_accounts`
6. Create `credentials` rows with `auth_type='pipedream_oauth'` and corresponding `credential_routes` so the broker can route to them

When a user connects a new app via Pipedream's hosted OAuth UI, call `POST /oauth-brokers/{broker_id}/sync` to pull it in without re-registering.

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
| `src/brokers/pipedream.py` | `PipedreamOAuthBroker` implementation, slug mapping |
| `src/routers/oauth_brokers.py` | CRUD API for managing broker configs and accounts |
| `src/routers/broker.py` | Vault-first fallback chain that consults the registry |
| `alembic/versions/0001_baseline.py` (+ `0002`, `0003`) | Authoritative schema for the OAuth-broker tables |
