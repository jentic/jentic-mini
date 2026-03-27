# Tutorial: From Zero to Agent-Ready in Two Examples

This tutorial walks through two real examples that show what Jentic Mini does and why it matters. By the end you'll have an agent that can call live APIs — with credentials it never sees and permissions you control.

**What you'll need:**
- Jentic Mini running (`docker compose up -d` — see [Getting Started](../README.md#getting-started))
- A toolkit key (generated during first-time setup)
- For Part 2: a Google account and a free [Pipedream](https://pipedream.com) account

---

## Part 1: GitHub Public API (No Credentials)

This shows the core search → inspect → execute flow with zero setup. The GitHub public API doesn't require authentication for read-only access, so there's nothing to configure — just search, find, and call.

### Step 1 — Search for what you need

Ask Jentic Mini to find GitHub-related operations:

```bash
curl -s "http://localhost:8900/search?q=github+list+repositories+for+a+user" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY"
```

You'll get back a ranked list of matching operations. Each result includes a capability ID, a short description, and the API it belongs to:

```json
[
  {
    "id": "GET/api.github.com/users/{username}/repos",
    "type": "operation",
    "summary": "List repositories for a user.",
    "api": "api.github.com",
    ...
  },
  ...
]
```

This is what an agent does first: search for the operation that matches its intent.

### Step 2 — Inspect the operation

Before calling it, the agent can inspect the full operation details — parameters, response schema, and whether credentials are required:

```bash
curl -s "http://localhost:8900/inspect/GET/api.github.com/users/{username}/repos" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY"
```

The response includes the full OpenAPI operation spec, required parameters, and a direct execute link. The agent now knows exactly what to send.

### Step 3 — Execute through the broker

The agent calls the API through Jentic Mini's broker. The URL pattern is `/{host}/{path}`:

```bash
curl -s "http://localhost:8900/api.github.com/users/jentic/repos" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY"
```

The broker proxies the request to `api.github.com`, logs a trace, and returns the response. No credentials needed — GitHub's public API allows unauthenticated reads.

**What just happened:** The agent searched for an API, inspected it, and called it — all through Jentic Mini. The broker handled the proxying and recorded a trace. For a public API this is straightforward, but it establishes the pattern: every API call goes through the broker, which means every call can be traced, credentialled, and governed.

### Viewing the trace

Every broker call produces a trace. Check it:

```bash
curl -s "http://localhost:8900/traces?limit=1" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY"
```

You'll see the operation called, the HTTP status, duration, and which toolkit key made the request. This is the observability layer — every API call your agent makes is recorded.

---

## Part 2: Gmail (OAuth Credentials + Fine-Grained Permissions)

Now for the real power. We're going to:

1. Connect a Gmail account via OAuth (the agent never sees the token)
2. Set permissions so the agent can **create drafts but not send emails**
3. Show the agent creating a draft through the broker

This is the example that makes people go "oh, I get it" — because Gmail's own OAuth scopes don't offer "drafts only, no send." Jentic Mini's permission rules give you control that the upstream API doesn't provide natively.

### Prerequisites

You'll need a Pipedream OAuth broker registered in Jentic Mini. If you haven't set this up yet, follow the [Pipedream Connect setup guide](PIPEDREAM.md#setup-required-before-first-use) — it takes about 5 minutes.

### Step 1 — Connect Gmail via OAuth

The agent generates a connect link and gives it to the human. One click, one OAuth consent screen, done.

```bash
curl -s -X POST "http://localhost:8900/oauth-brokers/pipedream/connect-link" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "app": "gmail",
    "external_user_id": "default",
    "label": "My Gmail"
  }'
```

Response:
```json
{
  "connect_link_url": "https://pipedream.com/_static/connect.html?token=ctok_...",
  "next_step": "Visit connect_link_url in your browser, authorise gmail, then call POST /oauth-brokers/pipedream/sync"
}
```

Open `connect_link_url` in your browser and complete the Google OAuth flow. You're granting access to Pipedream (which manages the token) — the token never touches Jentic Mini's API surface or the agent.

### Step 2 — Sync the token into the vault

After completing OAuth, the agent syncs the token:

```bash
curl -s -X POST "http://localhost:8900/oauth-brokers/pipedream/sync" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"external_user_id": "default"}'
```

The credential is now encrypted in the vault. The agent knows it exists but can never retrieve the token value.

### Step 3 — Set permissions: drafts yes, send no

By default, Jentic Mini's system safety rules deny all write operations (POST, PUT, PATCH, DELETE). This is intentional — write access must be explicitly granted.

We'll add rules that allow the agent to create and update drafts, but nothing else. The Gmail API uses these paths:

- `POST /gmail/v1/users/me/drafts` — create a draft
- `PUT /gmail/v1/users/me/drafts/{id}` — update a draft
- `POST /gmail/v1/users/me/messages/send` — send an email (we want to block this)

Set the permissions (requires a human session — log in at `http://localhost:8900` first):

```bash
curl -s -X PUT "http://localhost:8900/toolkits/default/credentials/YOUR_GMAIL_CREDENTIAL_ID/permissions" \
  -H "Cookie: jentic_session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "effect": "allow",
      "methods": ["POST", "PUT"],
      "path": "drafts"
    }
  ]'
```

This single rule allows POST and PUT to any path containing `drafts`. The system safety rules (appended automatically) handle the rest:

1. **Your rule:** Allow POST/PUT to paths matching `drafts` — **first match wins**
2. **System rule:** Deny requests to sensitive paths (`admin`, `billing`, `token`, etc.)
3. **System rule:** Deny all other write methods (POST, PUT, PATCH, DELETE)
4. **System rule:** Allow everything else (reads)

The result: the agent can create and update drafts, read emails, but **cannot send**. `POST /gmail/v1/users/me/messages/send` doesn't match `drafts`, so it falls through to the system deny rule.

You can also set this through the UI — navigate to **Toolkits → Default → Bound Credentials**, click **Permissions** on the Gmail credential, and add the rule there.

### Step 4 — Agent creates a draft

Now the agent can create a Gmail draft through the broker:

```bash
curl -s -X POST "http://localhost:8900/gmail.googleapis.com/gmail/v1/users/me/drafts" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "raw": "'$(echo -n "From: me\nTo: colleague@example.com\nSubject: Meeting notes\n\nHere are the notes from today." | base64)'"
    }
  }'
```

The broker:
1. Identifies the upstream host (`gmail.googleapis.com`)
2. Looks up the credential for this toolkit
3. Checks the permission rules — `POST` to a path containing `drafts` → allowed
4. Injects the OAuth token (via Pipedream's proxy) — the agent never sees it
5. Forwards the request to Gmail
6. Logs a trace and returns the response

The draft appears in the Gmail account's Drafts folder.

### Step 5 — Verify that sending is blocked

If the agent tries to send an email directly:

```bash
curl -s -X POST "http://localhost:8900/gmail.googleapis.com/gmail/v1/users/me/messages/send" \
  -H "X-Jentic-API-Key: YOUR_TOOLKIT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "raw": "'$(echo -n "From: me\nTo: someone@example.com\nSubject: Test\n\nThis should be blocked." | base64)'"
  }'
```

Response:
```json
{
  "error": "policy_denied",
  "message": "Request denied by policy: POST to /gmail/v1/users/me/messages/send is not allowed.",
  ...
}
```

The email is never sent. The agent gets a clear error, and the trace logs the denied attempt.

---

## What You Just Saw

**Part 1** showed the basic flow: search for an API, inspect it, call it through the broker. Every call is proxied and traced — even for public APIs with no credentials.

**Part 2** showed why this matters:

- **Credentials never touch the agent.** The OAuth token lives in the vault. The agent calls through the broker; the broker injects the token. If the agent is compromised, the attacker gets nothing.
- **Permissions go beyond what the API offers.** Gmail's OAuth scopes grant `gmail.compose` as a single scope — it doesn't distinguish between drafting and sending. Jentic Mini's permission rules add that boundary at the proxy layer, giving you control the upstream API doesn't provide.
- **The human stays in control.** Credential setup is a single OAuth click. Permission changes require a human session. The agent handles the conversation; the human just approves.

---

## Next Steps

- **Add more APIs:** Browse the public catalog at `http://localhost:8900/catalog` or search for any of the 10,000+ APIs in the Jentic catalog
- **Create additional toolkits:** Scope different agents to different APIs and permissions via `POST /toolkits`
- **Set up more OAuth apps:** Connect Slack, Google Drive, Salesforce, or any of 3,000+ apps via [Pipedream Connect](PIPEDREAM.md)
- **Explore workflows:** Multi-step Arazzo workflows chain operations across APIs — see [WORKFLOWS.md](WORKFLOWS.md)
- **Read the full API docs:** Swagger UI at `http://localhost:8900/docs`
