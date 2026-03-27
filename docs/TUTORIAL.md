# Tutorial: From Zero to Agent-Ready in Two Examples

This tutorial walks through two real examples that show what Jentic Mini does and why it matters. By the end your agent will be calling live APIs — with credentials it never sees and permissions you control.

> **Prerequisites:** You need Jentic Mini running and connected to your agent. If you haven't set that up yet, the fastest path is via the [Jentic skill on ClawHub](https://clawhub.com) — tell your OpenClaw agent *"install and set up the jentic skill from ClawHub"* and it will walk you through everything. For manual setup, see [Getting Started](../README.md#getting-started).

For Part 2 you'll also need a Google account and a free [Pipedream](https://pipedream.com) account (your agent will guide you through Pipedream setup when the time comes).

---

## Part 1: GitHub Public API (No Credentials)

This shows the core search → inspect → execute flow with zero setup. The GitHub public API doesn't require authentication for read-only access, so there's nothing to configure — just ask your agent to do something.

### Try it

Tell your agent:

> "Use Jentic to find the GitHub API for listing a user's repositories, then list the repos for the jentic org."

Behind the scenes, your agent will:

1. **Search** — call Jentic Mini's search endpoint to find the right GitHub operation
2. **Inspect** — look at the operation details to understand the parameters and response format
3. **Execute** — call the GitHub API through the broker

The broker proxies the request to `api.github.com`, logs a trace, and returns the response. No credentials needed — GitHub's public API allows unauthenticated reads.

### What just happened

Your agent searched for an API, inspected it, and called it — all through Jentic Mini. For a public API this is straightforward, but it establishes the pattern: **every API call goes through the broker**, which means every call can be traced, credentialled, and governed.

You can see the execution trace in the Jentic Mini UI at **Traces** (`http://localhost:8900/traces`), or ask your agent to show you the latest trace.

---

## Part 2: Gmail (OAuth Credentials + Fine-Grained Permissions)

This time we'll:

1. Connect a Gmail account via OAuth (the agent never sees the token)
2. Set permissions so the agent can **create drafts but not send emails**
3. Have the agent create a draft through the broker

Gmail's own OAuth scopes don't offer "drafts only, no send" — `gmail.compose` grants both. Jentic Mini's permission rules add that boundary at the proxy layer.

### Step 1 — Connect Gmail

Tell your agent:

> "Connect my Gmail account to Jentic so you can manage drafts for me."

Your agent will:

1. Generate an OAuth connect link via Jentic Mini's Pipedream integration
2. Give you a URL to click — this opens a Google OAuth consent page
3. You approve access in your browser (one click)
4. The agent syncs the token into Jentic Mini's encrypted vault

The OAuth token is stored encrypted and never returned via the API. Your agent knows the credential exists but can never retrieve the token value.

> **First time using OAuth?** If you haven't set up a Pipedream broker yet, your agent will guide you through it — or see the [Pipedream Connect setup guide](PIPEDREAM.md#setup-required-before-first-use). It's a one-time setup that takes about 5 minutes.

### Step 2 — Set permissions: drafts yes, send no

By default, Jentic Mini's system safety rules **deny all write operations** (POST, PUT, PATCH, DELETE). This is intentional — write access must be explicitly granted by a human.

The Gmail API uses these paths:
- `POST /gmail/v1/users/me/drafts` — create a draft
- `PUT /gmail/v1/users/me/drafts/{id}` — update a draft
- `POST /gmail/v1/users/me/messages/send` — send an email

We want to allow the first two and block the third. Open the Jentic Mini UI and navigate to **Toolkits → Default → Bound Credentials**. Find the Gmail credential, click **Permissions**, and add this rule:

| Effect | Methods | Path |
|--------|---------|------|
| Allow | POST, PUT | `drafts` |

This single rule allows POST and PUT to any path containing `drafts`. The system safety rules (appended automatically) handle the rest:

1. **Your rule:** Allow POST/PUT to paths matching `drafts` — **first match wins**
2. **System rule:** Deny requests to sensitive paths (`admin`, `billing`, `token`, etc.)
3. **System rule:** Deny all other write methods (POST, PUT, PATCH, DELETE)
4. **System rule:** Allow everything else (reads)

The result: the agent can create and update drafts, read emails, but **cannot send**. `POST /gmail/v1/users/me/messages/send` doesn't match `drafts`, so it falls through to the system deny rule.

### Step 3 — Agent creates a draft

Now tell your agent:

> "Draft an email to colleague@example.com with the subject 'Meeting notes' and a summary of what we discussed today."

The agent composes the email and calls the Gmail API through Jentic Mini's broker. Behind the scenes:

1. The broker identifies the upstream host (`gmail.googleapis.com`)
2. Looks up the credential for this toolkit
3. Checks the permission rules — `POST` to a path containing `drafts` → **allowed**
4. Injects the OAuth token (via Pipedream's proxy) — the agent never sees it
5. Forwards the request to Gmail
6. Logs a trace and returns the response

The draft appears in your Gmail Drafts folder. You can review and send it yourself.

### Step 4 — Verify that sending is blocked

Try telling your agent:

> "Send an email directly to someone@example.com saying hello."

The agent will attempt to call the Gmail send endpoint. Jentic Mini blocks it:

```json
{
  "error": "policy_denied",
  "message": "Request denied by policy: POST to /gmail/v1/users/me/messages/send is not allowed."
}
```

The email is never sent. The agent gets a clear error explaining why, and the denied attempt is recorded in the trace log. Your agent can explain to you what happened and suggest requesting additional permissions if needed.

---

## What You Just Saw

**Part 1** showed the basic flow: the agent searches for an API, inspects it, and calls it through the broker. Every call is proxied and traced — even for public APIs with no credentials.

**Part 2** showed why this matters:

- **Credentials never touch the agent.** The OAuth token lives in the vault. The agent calls through the broker; the broker injects the token. If the agent is compromised, the attacker gets nothing.
- **Permissions go beyond what the API offers.** Gmail's OAuth scopes grant `gmail.compose` as a single scope — it doesn't distinguish between drafting and sending. Jentic Mini's permission rules add that boundary at the proxy layer, giving you control the upstream API doesn't provide.
- **The human stays in control.** Credential setup is a single OAuth click. Permission changes require a human session. The agent handles the conversation; the human just approves.

---

## Next Steps

- **Add more APIs** — ask your agent to search the Jentic catalog for any API you use, or browse at `http://localhost:8900/catalog`
- **Connect more OAuth apps** — Slack, Google Drive, Salesforce, and 3,000+ more via [Pipedream Connect](PIPEDREAM.md)
- **Create additional toolkits** — scope different agents to different APIs and permissions
- **Explore workflows** — multi-step Arazzo workflows chain operations across APIs — see [WORKFLOWS.md](WORKFLOWS.md)
- **Read the full API docs** — Swagger UI at `http://localhost:8900/docs`
