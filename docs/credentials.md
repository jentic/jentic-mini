# Credentials Guide

## The Vault

All credential values are encrypted at rest using [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption.

**Encryption key:** `JENTIC_VAULT_KEY` environment variable. If absent or invalid at startup, a new key is auto-generated and written to `data/vault.key`. Keep this file safe — losing it means all stored credentials are unrecoverable.

**Write-only semantics:** Credential values are accepted by POST/PATCH endpoints but **never returned**. GET and list endpoints return credential metadata (id, label, api_id, auth_type, identity, server_variables, routes, scheme, timestamps) — the encrypted `value` is never exposed after write. There is no way to retrieve a plaintext credential value through the API once stored. (`identity` is non-secret — it typically holds a username or account ID, and is included in responses.)

---

## Creating a Credential

```http
POST /credentials
Content-Type: application/json

{
  "label": "ElevenLabs API Key",
  "value": "sk-...",
  "api_id": "api.elevenlabs.io",
  "auth_type": "apiKey"
}
```

Field meanings:

| Field | Purpose |
|---|---|
| `label` | Human-readable name (for display only) |
| `value` | The primary secret — API key, token, or password. Encrypted on write, never returned |
| `identity` | Optional identity — username, client ID, account SID. Required for `basic` auth and compound apiKey schemes using the canonical `Identity` scheme |
| `api_id` | Which API this credential is for (must match `apis.id`) |
| `auth_type` | How this credential authenticates: `bearer`, `basic`, `apiKey`, or `none` |
| `server_variables` | Optional JSON object of values for OpenAPI `servers[].variables` — see [server-variables.md](server-variables.md) |

`pipedream_oauth` is a reserved internal `auth_type` written by the Pipedream sync flow; it cannot be set via `POST /credentials`.

The `api_id` and any declared `credential_routes` are what the broker uses to match credentials to requests.

---

## Binding a Credential to a Toolkit

Credentials are stored globally but only injected for toolkits that have explicitly bound them.

```http
POST /toolkits/{toolkit_id}/credentials
Content-Type: application/json

{
  "credential_id": "uuid-of-credential"
}
```

When the broker receives a request with a toolkit key, it only considers credentials bound to that toolkit. A credential can be bound to multiple toolkits (shared credentials).

---

## Registering Auth for an API (The Overlay Flywheel)

Many real-world OpenAPI specs have missing or incorrect security scheme definitions. Jentic Mini handles this via overlays — OpenAPI Overlay 1.0 documents that patch the stored spec. Overlays start as **pending** and auto-confirm the first time a broker call using them returns a 2xx.

### Step-by-step

**1. Try the broker call**

```bash
curl http://localhost:8900/api.discourse.example.com/latest.json \
  -H "X-Jentic-API-Key: $KEY"
```

If the API has no security scheme declared, the broker returns a 409 pointing to the overlay endpoint:

```json
{
  "error": "no_security_scheme",
  "message": "API 'api.discourse.example.com' has no security scheme declared. Submit an OpenAPI overlay to add one.",
  "submit_to": "POST /apis/api.discourse.example.com/overlays"
}
```

If credentials are missing for an API that does have a scheme, the broker returns 403 `policy_denied` instead.

**2. Submit an OpenAPI overlay adding the security scheme**

```http
POST /apis/{api_id}/overlays
Content-Type: application/json

{
  "overlay": {
    "overlay": "1.0.0",
    "info": {"title": "Add apiKey scheme", "version": "1.0.0"},
    "actions": [
      {
        "target": "$",
        "update": {
          "components": {
            "securitySchemes": {
              "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Api-Key"}
            }
          }
        }
      },
      {
        "target": "$.paths[*][*]",
        "update": {"security": [{"ApiKeyAuth": []}]}
      }
    ]
  }
}
```

The overlay starts as `pending`. See the full overlay shape and targets (including compound apiKey schemes like Discourse's `Api-Key` + `Api-Username`) in the `POST /apis/{api_id}/overlays` endpoint docs at `/docs`.

**3. Create a credential bound to that API**

```http
POST /credentials
{
  "label": "Discourse API Key",
  "value": "abc123...",
  "api_id": "api.discourse.example.com",
  "auth_type": "apiKey"
}
```

**4. Bind to your toolkit**

```http
POST /toolkits/{toolkit_id}/credentials
{"credential_id": "uuid"}
```

**5. Retry the broker call**

On the first HTTP 2xx response, the first pending overlay for this API auto-flips to `confirmed`. The scheme is now part of the merged spec for all toolkits.

### Scheme Types and Injection Shape

The broker selects one of the merged security schemes at request time and builds the auth header from the matching credential's fields:

| OpenAPI scheme | Credential `auth_type` | Injects |
|---|---|---|
| `{type: "http", scheme: "bearer"}` | `bearer` | `Authorization: Bearer {value}` |
| `{type: "http", scheme: "basic"}` | `basic` | `Authorization: Basic base64("{identity ?? 'token'}:{value}")` |
| `{type: "apiKey", in: "header", name: "..."}` | `apiKey` | Request header with the declared name |

apiKey schemes declared with `in: "query"` or `in: "cookie"` are parsed but not currently injected — the broker logs a warning and skips them. Add them as header schemes via overlay if you can.

---

## Broker Injection Mechanics

When the broker receives a request for `/{host}/{path}`, it resolves credentials roughly as follows:

1. **Identify the upstream host** from the URL path (e.g. `api.elevenlabs.io`).
2. **Find matching credentials** via the `credential_routes` table (host + optional path prefix), scoped to the caller's toolkit.
3. **Load merged security schemes** for the API — OpenAPI spec schemes plus any confirmed/pending overlays.
4. **Match a credential to a scheme** by `auth_type` (and scheme-specific disambiguators), then build and inject the auth header.
5. **Forward the request** to the upstream and return the response verbatim.

If the caller supplies `X-Jentic-Credential: <id>` or `X-Jentic-Service: <service>`, the broker uses that as a hard override / preferred-match hint. When two credentials match ambiguously and the caller gave no hint, the broker returns `409 CREDENTIAL_AMBIGUOUS` with an `X-Jentic-Credential-Ambiguous: true` response header.

If **no credential matches** and the request is authenticated, the broker returns `403 policy_denied`. If the **API has no security scheme at all**, the broker returns `409 no_security_scheme` pointing at `POST /apis/{api_id}/overlays`.

See [broker-cli.md](broker-cli.md) for credential selection headers and simulate mode.

---

## Managing Toolkits and Keys

### Create a toolkit

```http
POST /toolkits
{"name": "My Agent Toolkit"}
```

### Issue an API key for a toolkit

```http
POST /toolkits/{toolkit_id}/keys
{
  "label": "Agent instance 1",
  "allowed_ips": ["192.168.1.0/24"]
}
```

Returns the key once. Store it — it cannot be retrieved again. If `allowed_ips` is omitted, the key inherits the trusted-subnet allowlist (RFC-1918 + loopback + `JENTIC_TRUSTED_SUBNETS` extras). See [auth.md](auth.md).

### Revoke a key

```http
DELETE /toolkits/{toolkit_id}/keys/{key_id}
```

Soft delete — sets `revoked_at`. Existing requests using that key will fail immediately.

### List active keys (metadata only, no values)

```http
GET /toolkits/{toolkit_id}/keys
```

---

## Security Notes

- The vault key (`JENTIC_VAULT_KEY` / `data/vault.key`) must be backed up separately. It is not stored in git.
- Credential values are never logged, never returned, and never passed to subprocess environments.
- The `env_var` column on a credential row is a legacy UNIQUE identifier derived from the credential ID. It is not a lookup key and does not correspond to any environment variable on the host.
- Per-key IP restrictions (`allowed_ips`) are evaluated against the `X-Forwarded-For` header when behind a proxy, or the direct client IP.
- Human admin sessions (via login) bypass toolkit scoping for credential management.
