# Tutorial: Gmail Drafts With Agent Permissions

This tutorial connects Gmail to Jentic Mini and shows how the permissions model works in practice. Your agent will try to create a draft, get blocked, request access, and then succeed — all through natural conversation.

Gmail's own OAuth scopes don't offer "drafts only, no send" — `gmail.compose` grants both. Jentic Mini's permission rules add that boundary at the proxy layer.

> **Prerequisites:** You need Jentic Mini running and connected to your agent. If you haven't set that up yet, the fastest path is via the [Jentic skill on ClawHub](https://clawhub.com) — tell your OpenClaw agent *"install and set up the jentic skill from ClawHub"* and it will walk you through everything. For manual setup, see [Getting Started](../README.md#getting-started).

You'll also need a Google account and a free [Pipedream](https://pipedream.com) account (your agent will guide you through Pipedream setup if it's your first time).

---

## Step 1 — Connect Gmail

Tell your agent:

> "Connect my Gmail account to Jentic so you can manage drafts for me."

Your agent will:

1. Generate an OAuth connect link via Jentic Mini's Pipedream integration
2. Give you a URL to click — this opens a Google OAuth consent page
3. You approve access in your browser (one click)
4. The agent syncs the token into Jentic Mini's encrypted vault

The OAuth token is stored encrypted and never returned via the API. Your agent knows the credential exists but can never retrieve the token value.

> **First time using OAuth?** If you haven't set up a Pipedream broker yet, your agent will guide you through it — or see the [Pipedream Connect setup guide](PIPEDREAM.md#setup-required-before-first-use). It's a one-time setup that takes about 5 minutes.

## Step 2 — Try to create a draft

Now tell your agent:

> "Draft an email to colleague@example.com with the subject 'Meeting notes' and a summary of what we discussed today."

The agent will compose the email and attempt to call the Gmail API through Jentic Mini's broker. It will be **blocked** — by default, Jentic Mini's system safety rules deny all write operations (POST, PUT, PATCH, DELETE). The agent hasn't been granted permission to create drafts yet.

The agent will get back an error like:

```json
{
  "error": "policy_denied",
  "message": "Request denied by policy: POST is not allowed."
}
```

## Step 3 — Grant permission

Your agent should recognise the policy denial and offer to request access. If it doesn't, tell it:

> "Request permission to create and update Gmail drafts."

The agent will submit an access request to Jentic Mini, which generates an approval link. The agent gives you the link — click it to open the Jentic Mini approval page.

On the approval page you'll see what the agent is requesting. Approve it, and the permission rule is applied:

| Effect | Methods | Path |
|--------|---------|------|
| Allow | POST, PUT | `drafts` |

This single rule allows POST and PUT to any path containing `drafts`. The system safety rules (appended automatically) handle the rest:

1. **Your rule:** Allow POST/PUT to paths matching `drafts` — **first match wins**
2. **System rule:** Deny requests to sensitive paths (`admin`, `billing`, `token`, etc.)
3. **System rule:** Deny all other write methods (POST, PUT, PATCH, DELETE)
4. **System rule:** Allow everything else (reads)

The result: the agent can create and update drafts, read emails, but **cannot send**. `POST /gmail/v1/users/me/messages/send` doesn't match `drafts`, so it falls through to the system deny rule.

## Step 4 — Create the draft

Tell your agent to try again:

> "Try drafting that email again."

This time the broker checks the permission rules, finds the `drafts` allow rule, injects the OAuth token, and forwards the request to Gmail. The draft appears in your Gmail Drafts folder. You can review and send it yourself.

## Step 5 — Verify that sending is blocked

Try telling your agent:

> "Send an email directly to someone@example.com saying hello."

The agent will attempt to call the Gmail send endpoint. Jentic Mini blocks it — the send path doesn't match `drafts`, so it falls through to the system deny rule. The email is never sent, and the denied attempt is recorded in the trace log.

---

## What this demonstrated

- **Credentials never touch the agent.** The OAuth token lives in the vault. The agent calls through the broker; the broker injects the token.
- **Permissions go beyond what the API offers.** Gmail's OAuth scopes grant `gmail.compose` as a single scope — it doesn't distinguish between drafting and sending. Jentic Mini's permission rules add that boundary at the proxy layer.
- **The agent hits a wall and recovers.** The deny → request → approve → retry flow is the normal way agents gain access. The human approves once; the agent remembers.

---

## Next steps

- **Add more APIs** — ask your agent to search the Jentic catalog for any API you use, or browse at `http://localhost:8900/catalog`
- **Connect more OAuth apps** — Slack, Google Drive, Salesforce, and 3,000+ more via [Pipedream Connect](PIPEDREAM.md)
- **Create additional toolkits** — scope different agents to different APIs and permissions
- **Explore workflows** — multi-step Arazzo workflows chain operations across APIs — see [WORKFLOWS.md](WORKFLOWS.md)
- **Read the full API docs** — Swagger UI at `http://localhost:8900/docs`
