# Tutorial: Notion With Agent Permissions

This tutorial connects the Notion API to Jentic Mini and shows how the permissions model works in practice. Your agent will try to create a page, get blocked, request access, and then succeed — all through natural conversation.

> **Prerequisites:** You need Jentic Mini running and connected to your agent. If you haven't set that up yet, the fastest path is via the [Jentic skill on ClawHub](https://clawhub.com) — tell your OpenClaw agent *"install and set up the jentic skill from ClawHub"* and it will walk you through everything. For manual setup, see [Getting Started](../README.md#getting-started).

You'll also need a Notion account with a [Notion integration](https://www.notion.so/my-integrations) (free to create).

---

## Step 1 — Create a Notion integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and click **New integration**
2. Give it a name (e.g. "Jentic Agent"), select your workspace, and click **Submit**
3. Copy the **Internal Integration Secret** (starts with `ntn_`)

In Notion, open the page or database you want the agent to access, click **...** → **Connections** → **Connect to** and select your integration. Notion requires this explicit sharing step — the integration can only see pages it's been invited to.

## Step 2 — Add the credential to Jentic Mini

Tell your agent:

> "Add my Notion API key to Jentic. The API is notion.com/notion-api and the auth type is bearer."

Your agent will prompt you for the token value. Paste in your `ntn_` secret. The credential is encrypted in the vault and never returned via the API — your agent knows it exists but can never retrieve the value.

## Step 3 — Try to create a page

Tell your agent:

> "Use the Notion API to create a new page in my workspace with the title 'Meeting Notes' and some bullet points."

The agent will search for the right Notion operation, find `POST /v1/pages`, and attempt to call it through Jentic Mini's broker. It will be **blocked** — by default, Jentic Mini's system safety rules deny all write operations (POST, PUT, PATCH, DELETE). The agent hasn't been granted permission to create pages yet.

The agent will get back an error like:

```json
{
  "error": "policy_denied",
  "message": "Request denied by policy: POST is not allowed."
}
```

## Step 4 — Grant permission

Your agent should recognise the policy denial and offer to request access. If it doesn't, tell it:

> "Request permission to create and update Notion pages."

The agent will submit an access request to Jentic Mini, which generates an approval link. The agent gives you the link — click it to open the Jentic Mini approval page.

On the approval page you'll see what the agent is requesting. Approve it, and the permission rule is applied:

| Effect | Methods | Path |
|--------|---------|------|
| Allow | POST, PUT, PATCH | `pages` |

This rule allows the agent to create and update pages. The system safety rules (appended automatically) handle the rest:

1. **Your rule:** Allow POST/PUT/PATCH to paths matching `pages` — **first match wins**
2. **System rule:** Deny requests to sensitive paths (`admin`, `billing`, `token`, etc.)
3. **System rule:** Deny all other write methods (POST, PUT, PATCH, DELETE)
4. **System rule:** Allow everything else (reads)

The result: the agent can create and update pages, search and read content, but cannot delete pages or modify databases.

## Step 5 — Create the page

Tell your agent to try again:

> "Try creating that Notion page again."

This time the broker checks the permission rules, finds the `pages` allow rule, injects the bearer token, and forwards the request to Notion. The page appears in your workspace.

## Step 6 — Verify that deletes are blocked

Try telling your agent:

> "Delete that page from Notion."

The agent will attempt to call the Notion API with a DELETE or an archive PATCH. If the path doesn't match `pages` or the method isn't in the allow list, Jentic Mini blocks it. The page stays put, and the denied attempt is recorded in the trace log.

---

## What this demonstrated

- **Credentials never touch the agent.** The API token lives in the vault. The agent calls through the broker; the broker injects the token.
- **Write access is opt-in.** Every write operation is denied by default. The agent hits a wall, requests access, and the human approves — once.
- **The agent hits a wall and recovers.** The deny → request → approve → retry flow is the normal way agents gain access. The human approves once; the agent remembers.

---

## Next: Gmail with OAuth and fine-grained permissions

The Notion example uses a simple API key. For APIs that require OAuth (Gmail, Slack, Google Drive, etc.), Jentic Mini integrates with [Pipedream Connect](PIPEDREAM.md) to handle the OAuth flow — your agent generates a link, you click it, and the token is stored in the vault automatically.

The [Gmail tutorial](TUTORIAL-GMAIL.md) walks through connecting Gmail and setting permissions so your agent can draft emails but not send them — a boundary that Gmail's own OAuth scopes don't offer.

---

## More next steps

- **Add more APIs** — ask your agent to search the Jentic catalog for any API you use, or browse at `http://localhost:8900/catalog`
- **Connect OAuth apps** — Slack, Google Drive, Salesforce, and 3,000+ more via [Pipedream Connect](PIPEDREAM.md)
- **Create additional toolkits** — scope different agents to different APIs and permissions
- **Explore workflows** — multi-step Arazzo workflows chain operations across APIs — see [WORKFLOWS.md](WORKFLOWS.md)
- **Read the full API docs** — Swagger UI at `http://localhost:8900/docs`
