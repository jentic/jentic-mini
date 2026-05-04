# self-registration.md — Jentic Mini in Jentic Mini

## Overview

On first boot, Jentic Mini registers **itself** as an API in its own catalog. This means agents can discover, request access to, and call Jentic Mini's own management endpoints (create toolkits, manage credentials, etc.) through the same broker + access-request flow used for any external API (ElevenLabs, OpenAI, GitHub, etc.).

This is intentional. Jentic Mini's management API is just another API.

---

## What happens at startup

1. **Spec import** — Jentic Mini fetches its own `GET /openapi.json` and registers all endpoints under `{JENTIC_PUBLIC_HOSTNAME}` in the catalog. If already registered (subsequent boots), this is skipped.

2. **Internal credential** — A toolkit API key is generated and stored in the vault as a credential with:
   - `id`: `{JENTIC_PUBLIC_HOSTNAME}` (e.g. `jentic-mini.example.com`)
   - `api_id`: `{JENTIC_PUBLIC_HOSTNAME}`
   - `label`: `Jentic Mini Admin Key`
   - `scheme_name`: `JenticApiKey`
   - Value: a freshly-generated `tk_xxx` admin key

   If this credential already exists (subsequent boots), it is **not** regenerated — the existing key remains valid.

3. The credential lives in the **default toolkit** (implicitly accessible to all, per the default toolkit membership rules).

---

## Agent access flow

An agent holding a scoped toolkit key cannot call Jentic Mini management endpoints by default. The write-methods system safety rule blocks all POSTs. To gain access, the agent uses the standard access-request flow:

```
# 1. Agent discovers the endpoint it needs
GET /search?q=create toolkit
→ returns: POST/jentic-mini.example.com/toolkits

# 2. Agent checks what credentials are available
GET /credentials?api_id=jentic-mini.example.com
→ returns: { id: "jentic-mini.example.com", label: "Jentic Mini Admin Key" }

# 3. Agent files an access-request
POST /toolkits/{my-toolkit}/access-requests
{
  "type": "grant",
  "credential_id": "jentic-mini.example.com",
  "rules": [
    { "effect": "allow", "methods": ["POST"], "path": "toolkits" }
  ],
  "reason": "I need to create and manage toolkits"
}

# 4. Human approves via UI
GET /toolkits/{my-toolkit}/access-requests/approve/{req_id}

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

An agent that has been granted the admin key *and* the permission to approve access-requests would be self-securing. **This should never be permitted.** The approve/deny endpoints require a human JWT session — toolkit API keys cannot call them, by design. This constraint must not be removed.

### Self-hosted note

For self-hosted deployments, the internal credential key is as sensitive as the human admin account. It should not be committed, logged, or exposed. The vault encrypts it at rest; the API never returns its value.

---

## Broker routing

When the broker receives a request to `{JENTIC_PUBLIC_HOSTNAME}/...`, it routes to `http://localhost:{PORT}/...` (or the internal Docker network address). This is handled by a special-case rewrite in the broker: if the target host matches `JENTIC_PUBLIC_HOSTNAME`, use the internal address rather than attempting external DNS resolution.

This avoids a round-trip through the public network and works correctly inside Docker without requiring Tailscale or external DNS.

---

## What needs building

- [ ] `startup.py` (or lifespan hook in `main.py`): auto-import own spec + auto-create internal credential
- [ ] Broker localhost rewrite: detect `JENTIC_PUBLIC_HOSTNAME` as target, route to `localhost:{PORT}`
- [ ] Credential creation should be idempotent (skip if `jentic-mini.example.com` already exists)
- [ ] Spec import should be idempotent (skip if already registered)
- [ ] Startup log: emit a clear message when self-registration runs vs. is skipped

---

## Open questions

1. **Key rotation** — if the human regenerates the admin key (via `POST /default-api-key/generate`), the internal credential in the vault becomes stale. Should startup detect and refresh it?
2. **Permissions template** — should we ship a recommended `rules` template for common Jentic Mini access patterns (read-only, toolkit-manager, full-admin)?
3. **Multiple instances** — in a multi-instance deployment, each instance would register under its own hostname. Credentials are not shared across instances by default. Is cross-instance brokering in scope?
