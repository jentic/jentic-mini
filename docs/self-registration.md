# Self-Registration — Jentic Mini in Jentic Mini

## Overview

On first boot, Jentic Mini registers **itself** as an API in its own catalog. This means agents can discover, request access to, and call Jentic Mini's own management endpoints (create toolkits, manage credentials, etc.) through the same broker + access-request flow used for any external API (ElevenLabs, OpenAI, GitHub, etc.).

This is intentional. Jentic Mini's management API is just another API.

The self-registration lifecycle hook lives in `src/startup.py`.

---

## What happens at startup

1. **Spec import** — Jentic Mini materialises its own OpenAPI spec via FastAPI's `get_openapi()`, rewrites `servers[0].url` to the public hostname, saves it to `data/specs/jentic-mini.json`, and registers it in the catalog. If already registered (subsequent boots), this is skipped.

2. **Internal credential** — A toolkit API key is generated and stored in the vault as a credential with:
   - `id`: `jentic-mini` (literal; not the hostname)
   - `api_id`: the resolved API ID (usually `{JENTIC_PUBLIC_HOSTNAME}`)
   - `label`: `Jentic Mini Admin Key`
   - `auth_type`: `JenticApiKey` (written via the legacy `scheme_name` parameter in `src/vault.py`; see [decisions.md](decisions.md))
   - Value: a freshly-generated `tk_xxx` admin key

   If this credential already exists (subsequent boots), it is **not** regenerated — the existing key remains valid.

3. The credential is registered as a toolkit key in the **default toolkit** so the default agent key can use it.

4. **Install registration** — On first successful boot, a random UUID is generated in `data/install-id.txt` and POSTed to `https://api.jentic.com/api/v1/register-install`. Opt-out via `JENTIC_TELEMETRY=off`. See the top-level [README.md](../README.md#telemetry--community-contributions) and `src/startup.py`.

---

## Agent access flow

An agent holding a scoped toolkit key cannot call Jentic Mini management endpoints by default — the default policy blocks write methods. To gain access, the agent uses the standard access-request flow:

```
# 1. Agent discovers the endpoint it needs
GET /search?q=create toolkit
→ returns: POST/jentic-mini.example.com/toolkits

# 2. Agent checks what credentials are available
GET /credentials?api_id=jentic-mini.example.com
→ returns: { id: "jentic-mini", label: "Jentic Mini Admin Key", ... }

# 3. Agent files an access-request
POST /toolkits/{my-toolkit}/access-requests
{
  "type": "grant",
  "credential_id": "jentic-mini",
  "rules": [
    { "effect": "allow", "methods": ["POST"], "path": "toolkits" }
  ],
  "reason": "I need to create and manage toolkits"
}

# 4. Human opens the approval UI
#    GET /toolkits/{my-toolkit}/access-requests/approve/{req_id}
#    redirects (302) to the SPA page /approve/{toolkit_id}/{req_id},
#    which on click POSTs:
POST /toolkits/{my-toolkit}/access-requests/{req_id}/approve   # human session only

# 5. Agent calls Jentic Mini through the broker
POST /jentic-mini.example.com/toolkits
{ "name": "my-new-toolkit", "description": "..." }
→ broker injects admin key → Jentic Mini creates the toolkit
```

---

## Security model

### The approval gate is the trust boundary

The human approval step is what prevents privilege escalation. An agent cannot grant itself access to the admin key — it can only *request* it. A human must approve.

### The internal key is admin-scoped

The credential stored in the vault is a full admin toolkit key. This means any toolkit that receives a grant + broad permission rules could perform destructive operations (delete toolkits, revoke credentials, etc.).

**Mitigation:** The access-request's `rules` field scopes what the agent can actually do with the credential, even after it's granted. The human approver should review the rules carefully — granting the credential with `POST /toolkits` only is very different from granting it with all methods and no path restriction.

### Circular trust

An agent that has been granted the admin key *and* the permission to approve access-requests would be self-securing. **This should never be permitted.** The approve/deny endpoints require a human JWT session — toolkit API keys cannot call them, by design. See [auth.md](auth.md). This constraint must not be removed.

### Self-hosted note

For self-hosted deployments, the internal credential key is as sensitive as the human admin account. It should not be committed, logged, or exposed. The vault encrypts it at rest; the API never returns its value.

---

## Broker routing

When the broker receives a request whose upstream host matches `JENTIC_PUBLIC_HOSTNAME` (or the request's `Host` header, or `localhost` / `127.0.0.1`), it rewrites the target URL to `http://localhost:{JENTIC_INTERNAL_PORT}/...` rather than attempting external DNS resolution.

This avoids a round-trip through the public network and works correctly inside Docker without requiring Tailscale or external DNS.

---

## Open questions

1. **Key rotation** — if the human regenerates the admin key (via `POST /default-api-key/generate`), the internal credential in the vault becomes stale. Should startup detect and refresh it?
2. **Permissions template** — should we ship a recommended `rules` template for common Jentic Mini access patterns (read-only, toolkit-manager, full-admin)?
3. **Multiple instances** — in a multi-instance deployment, each instance would register under its own hostname. Credentials are not shared across instances by default. Is cross-instance brokering in scope?
