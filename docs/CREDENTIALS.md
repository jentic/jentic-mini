# Credentials Guide

## The Vault

All credential values are encrypted at rest using [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption.

**Encryption key:** `JENTIC_VAULT_KEY` environment variable. If absent or invalid at startup, a new key is auto-generated and written to `data/vault.key`. Keep this file safe — losing it means all stored credentials are unrecoverable.

**Write-only semantics:** Credential values are accepted by POST/PATCH endpoints but **never returned**. GET and list endpoints return only `id`, `label`, `api_id`, and `scheme_name`. There is no way to retrieve a plaintext credential value through the API once stored.

---

## Creating a Credential

```http
POST /credentials
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "label": "ElevenLabs API Key",
  "env_var": "ELEVENLABS_APIKEYAUTH",
  "value": "sk-...",
  "api_id": "api.elevenlabs.io",
  "scheme_name": "ApiKeyAuth"
}
```

Field meanings:

| Field | Purpose |
|---|---|
| `label` | Human-readable name (for display only) |
| `value` | The primary secret — API key, token, or password. Encrypted on write, never returned |
| `identity` | Optional identity — username, client ID, account SID. Required for `basic`/`digest` auth and compound apiKey schemes using the canonical `Identity` scheme name |
| `api_id` | Which API this credential is for (must match `apis.id`) |
| `scheme_name` | Which security scheme in the API's spec this credential satisfies |

The `api_id` + `scheme_name` pair is what the broker uses to match credentials to requests.

---

## Binding a Credential to a Collection

Credentials are stored globally but only injected for collections that have explicitly bound them.

```http
POST /collections/{collection_id}/credentials
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "credential_id": "uuid-of-credential"
}
```

When the broker receives a request with a collection key, it only considers credentials bound to that collection. A credential can be bound to multiple collections (shared credentials).

---

## Registering Auth for an API (The Scheme Flywheel)

Many real-world OpenAPI specs have missing or incorrect security scheme definitions. JPE handles this gracefully via a flywheel pattern that progressively improves auth coverage.

### Step-by-step

**1. Try the broker call**

```bash
curl http://localhost:8900/api.discourse.example.com/latest.json \
  -H "X-Jentic-API-Key: $KEY"
```

If no credential/scheme is found, the broker returns:
```json
{
  "error": "no_credentials_found",
  "message": "No credentials configured for api.discourse.example.com",
  "hint": "Register a security scheme: POST /apis/api.discourse.example.com/scheme"
}
```

**2. Register a security scheme**

```http
POST /apis/{api_id}/scheme
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "type": "apiKey",
  "config": {
    "location": "header",
    "name": "Api-Key"
  }
}
```

This creates a **pending overlay** — an OpenAPI overlay document that adds the security scheme to the API's spec.

**3. Create a credential bound to that scheme**

```http
POST /credentials
{
  "label": "Discourse API Key",
  "env_var": "DISCOURSE_APIKEYAUTH",
  "value": "abc123...",
  "api_id": "api.discourse.example.com",
  "scheme_name": "ApiKeyAuth"
}
```

**4. Bind to your collection**

```http
POST /collections/{collection_id}/credentials
{"credential_id": "uuid"}
```

**5. Retry the broker call**

On the first HTTP 2xx response, JPE automatically flips the overlay status from `pending` to `confirmed`. The scheme is now part of the permanent API catalog for all collections.

### Supported Scheme Types

| Type | Config fields | Injects |
|---|---|---|
| `apiKey` (header) | `location: "header"`, `name: "X-Api-Key"` | Request header |
| `apiKey` (query) | `location: "query"`, `name: "api_key"` | Query parameter |
| `apiKey` (cookie) | `location: "cookie"`, `name: "session"` | Cookie header |
| `bearer` | (none) | `Authorization: Bearer {value}` |
| `basic` | (none) | `Authorization: Basic base64("{identity ?? 'token'}:{value}")` — set `identity` on the credential for user/password APIs |
| `oauth2_client_credentials` | `token_url`, `client_id`, `client_secret` | `Authorization: Bearer {fetched_token}` |
| `multiple_headers` | `headers: [{name, source_env_var}]` | Multiple headers simultaneously |

### Raw Overlay Registration

For full control, you can POST an OpenAPI overlay document directly:

```http
POST /apis/{api_id}/overlays
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "overlay": { ... OpenAPI overlay document ... }
}
```

---

## Broker Injection Mechanics

When the broker receives a request for `/{host}/{path}`, it resolves credentials in this order:

1. **Identify the upstream host** from the URL path (e.g. `api.elevenlabs.io`)
2. **Find the API registration** whose `id` matches or is a parent domain of the host
3. **Get all credentials** in this collection bound to that `api_id`
4. **Get merged security schemes** — OpenAPI spec schemes + any confirmed overlays for this API
5. **For each credential**, match `scheme_name` to a scheme entry and build the appropriate auth header
6. **Inject headers** into the forwarded request

If no matching credential is found → 400 with `no_credentials_found` hint.

If the API has no security schemes (spec has none and no confirmed overlays) → 400 with hint to call `POST /apis/{api_id}/scheme`.

---

## Managing Collections and Keys

### Create a collection

```http
POST /collections
{"name": "My Agent Collection"}
```

### Issue an API key for a collection

```http
POST /collections/{collection_id}/keys
{
  "label": "Agent instance 1",
  "allowed_ips": ["192.168.1.0/24"]
}
```

Returns the key once. Store it — it cannot be retrieved again.

### Revoke a key

```http
DELETE /collections/{collection_id}/keys/{key_id}
```

Soft delete — sets `revoked_at`. Existing requests using that key will fail immediately.

### List active keys (metadata only, no values)

```http
GET /collections/{collection_id}/keys
```

---

## Security Notes

- The vault key (`JENTIC_VAULT_KEY` / `data/vault.key`) must be backed up separately. It is not stored in git.
- Credential values are never logged, never returned, and never passed to subprocess environments.
- The `env_var` field (e.g. `ELEVENLABS_APIKEYAUTH`) is used as a vault lookup key — it does not correspond to any actual environment variable name in the host OS.
- Per-key IP restrictions (`allowed_ips`) are evaluated against the `X-Forwarded-For` header when behind a proxy, or the direct client IP.
- Human admin sessions (via login) bypass toolkit scoping for credential management.
