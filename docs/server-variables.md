# Self-Hosted & Multi-Tenant APIs: Server Variables

Some APIs don't have a fixed base URL — the hostname (and sometimes the path) depends on
where the software is deployed. Discourse, Jenkins, Home Assistant, Jira on-premise,
Gitea, and many other self-hosted tools all work this way.

OpenAPI 3.x handles this through **server variables**: template placeholders in the
`servers[].url` field that callers are expected to fill in. For example:

```yaml
servers:
  - url: "https://{host}"
    variables:
      host:
        description: "Hostname of your Discourse instance (e.g. forum.acme.com)"
        default: ""
```

Jentic supports server variables as a first-class concept. You configure the resolved
values alongside the credential that needs them, and the broker substitutes them at
routing time — no modified spec copy required.

---

## How It Works

1. **Spec declares variables** — either natively or via an overlay added by Jentic.
2. **You store resolved values with the credential** — a `server_variables` JSON object
   mapping variable name to the value for your specific instance.
3. **Broker substitutes at routing time** — before forwarding the request, the broker
   resolves `{variable}` placeholders in the base URL using the credential's stored values.

---

## Setting Up a Self-Hosted API

### Step 1 — Discover what variables the spec requires

```bash
GET /apis/{api_id}
```

Look for the `server_variables` field in the response. Variables with `required: true`
(no default) must be supplied in your credential.

```json
{
  "server_variables": {
    "host": {
      "default": null,
      "description": "Hostname of your Discourse instance",
      "required": true
    }
  }
}
```

You can also call `GET /inspect/{operation_id}` — the `server_variables` field will
show the spec's variable definitions and, if a credential is already configured, the
values currently stored.

### Step 2 — Create the credential with `server_variables`

```bash
POST /credentials
```

```json
{
  "label": "Acme Discourse",
  "api_id": "discourse.example.com",
  "auth_type": "apiKey",
  "value": "your-api-key",
  "identity": "your-username",
  "server_variables": {
    "host": "forum.acme.com"
  }
}
```

If you forget `server_variables` on an API that requires them, the `201` response will
include a `warning: server_variables_required` field listing what's missing, with a
`remediation` pointer to the PATCH endpoint.

### Step 3 — Execute via the broker

The broker URL uses the Jentic-resolved `api_id`, not your instance hostname:

```bash
GET /discourse.example.com/latest.json
```

The broker looks up your credential, finds `{"host": "forum.acme.com"}`, substitutes
the template, and routes to `https://forum.acme.com/latest.json`.

---

## Updating Variables

To change which instance a credential points at (e.g. after migration):

```bash
PATCH /credentials/{id}
```

```json
{
  "server_variables": {
    "host": "forum-new.acme.com"
  }
}
```

---

## Spec Doesn't Have Server Variables?

If an upstream spec hardcodes a default/example hostname rather than using variables,
submit an overlay to add them:

```bash
POST /apis/{api_id}/overlays
```

```json
{
  "overlay": "1.0.0",
  "info": { "title": "Add server variable", "version": "1.0.0" },
  "actions": [{
    "target": "$.servers[0]",
    "update": {
      "url": "https://{host}",
      "variables": {
        "host": {
          "default": "",
          "description": "Hostname of your instance"
        }
      }
    }
  }]
}
```

Once confirmed, the credential workflow above applies.

---

## Multi-Tenant SaaS

The same mechanism handles multi-tenant SaaS where each customer gets a subdomain
(`{tenant}.atlassian.com`, `{org}.zendesk.com`, etc.):

```json
{
  "server_variables": {
    "tenant": "acme"
  }
}
```

---

## Examples

| Software | Variable(s) | Example value |
|---|---|---|
| Discourse | `host` | `forum.acme.com` |
| Jenkins | `host` | `ci.acme.com` |
| Home Assistant | `host` | `10.0.0.3:8123` |
| Gitea | `host` | `git.acme.com` |
| Jira on-premise | `host` | `jira.acme.com` |
| Atlassian Cloud | `tenant` | `acme` |
| Zendesk | `subdomain` | `acme` |
