# Pipedream Connect Integration

Jentic Mini integrates with [Pipedream Connect](https://pipedream.com/connect) to provide OAuth authentication for 3,000+ SaaS apps — without implementing OAuth flows yourself or going through app certification with each platform.

> **Broker ID note:** All endpoints below use the path segment `{broker_id}` — the
> ID of a registered OAuth broker. On a fresh install with a single Pipedream
> broker registered, `{broker_id}` is `pipedream`. In multi-broker deployments it
> may be `pipedream-2`, a custom ID you passed at registration time, or something
> else entirely. Use `GET /oauth-brokers` to list the IDs.

## Why Pipedream Connect

OAuth is the auth standard used by every major SaaS platform (Gmail, Slack, Salesforce, GitHub, etc.). Implementing it properly requires:

- Registering OAuth clients with each platform
- Going through review/certification processes (Google, Slack, Salesforce all have this)
- Implementing the authorization code flow, token refresh, PKCE, etc.
- Handling token storage and rotation securely

Pipedream has done all of this for 3,000+ apps. Jentic Mini borrows that infrastructure: the user sees a Pipedream-hosted OAuth consent page, authorizes the app, and Pipedream stores the OAuth tokens. Jentic Mini stores the resulting `account_id` reference locally, and all subsequent API calls are routed through Pipedream's Connect proxy — which injects the OAuth token server-side before forwarding to the upstream API.

**Tradeoff:** End users see Pipedream branding during the OAuth flow. Acceptable for self-hosted/personal use. If you need white-label OAuth, Pipedream supports [custom OAuth clients](https://pipedream.com/docs/connect/managed-auth/oauth-clients/).

---

## Setup (required before first use)

### Step 1 — Create a Pipedream account and project

- Sign up at [pipedream.com](https://pipedream.com) (free tier available)
- Create a **project** in the Pipedream dashboard

### Step 2 — Create a Connect OAuth Client

The Connect OAuth client authenticates your Jentic Mini server against Pipedream's Connect API. This is a **workspace-level client** (not app-specific) and is shared across all your Pipedream projects.

1. Go to **[pipedream.com/settings/api](https://pipedream.com/settings/api)**
2. Click **New OAuth Client**
3. Give it a name (e.g. `jentic-mini`) and click **Create**
4. Copy your `client_id` and `client_secret` — **the secret is shown once only**

> **Note:** This is different from per-app OAuth clients (found at `pipedream.com/@/accounts/oauth-clients`). Those are for customising the OAuth client used when connecting individual apps like GitHub or Google — not required for basic Jentic Mini setup.

### Step 3 — Get your Project ID

In your Pipedream project, open **Settings** and copy the `project_id` (format: `proj_xxxxxxx`).

### Step 4 — Register the Pipedream OAuth broker in Jentic Mini

Broker registration requires a human session — agent keys cannot register or modify brokers. This is intentional: the `client_secret` must never flow through an agent-accessible path. The `client_secret` is Fernet-encrypted at rest in the local vault and is never returned via the API.

**Via the UI:**

1. Open **[http://localhost:8900/oauth-brokers](http://localhost:8900/oauth-brokers)** in your browser
2. Log in with your Jentic Mini admin account if prompted
3. Click **Add Broker**
4. Fill in: Type `pipedream`, your `client_id`, `client_secret`, `project_id`, `environment` (`development` or `production`), optional `support_email`
5. Click **Save**

**Via the API** (requires an authenticated human session):

```http
POST /oauth-brokers
Content-Type: application/json

{
  "type": "pipedream",
  "config": {
    "client_id": "oa_abc123",
    "client_secret": "pd_secret_xxxx",
    "project_id": "proj_abc123",
    "environment": "development",
    "support_email": "admin@example.com"
  }
}
```

The `config` object is nested — do **not** flatten these fields onto the top-level request body. The response includes the assigned `broker_id` (typically `pipedream` for the first broker).

> **Development environment note:** Pipedream's `development` environment is free and supports all Connect features, but limits you to 10 external users and requires you to be signed in to pipedream.com in the same browser when completing OAuth flows.

---

## How It Works

Once the broker is registered, the connect and sync operations are **open to agents** — any valid toolkit key can call them. No human login step is required. The recommended approach is to let your agent drive the flow: it generates the connect URL and surfaces it to the human for a single click approval. The human never needs to interact with Jentic Mini directly.

```
1. Agent calls POST /oauth-brokers/{broker_id}/connect-link
   → Jentic Mini authenticates with Pipedream using your registered broker credentials
   → Pipedream mints a one-time connect token
   → Jentic Mini returns a connect URL (expires ~1 hour)
   → Agent surfaces the URL to the human: "Click here to connect your Google Drive"

2. Human opens the URL in their browser
   → Must be signed in to pipedream.com (development environment requirement)
   → Sees Pipedream-hosted OAuth consent page for the target app
   → Completes OAuth (e.g. Google, Slack, GitHub)
   → Pipedream stores the access + refresh tokens under your project

3. Agent calls POST /oauth-brokers/{broker_id}/sync
   → Jentic Mini fetches the token from Pipedream and stores it in its local encrypted vault
   → Jentic Mini stores the Pipedream account_id reference locally
   → All subsequent API calls are proxied through Pipedream's Connect proxy

4. (Automatic) Token refresh _(planned)_
   → Token refresh on 401 is not yet wired into the broker's pipedream_oauth handler
   → For now, re-run POST /oauth-brokers/{broker_id}/sync to manually refresh tokens
```

You can also initiate connect-link manually via the Jentic Mini UI at `http://localhost:8900/oauth-brokers`, but letting the agent handle it is the recommended approach — it keeps the human interaction to a single OAuth approval click.

### Security boundary

| Operation | Who can call | Why |
|-----------|-------------|-----|
| Register broker (`POST /oauth-brokers`) | Human only | Injects `client_secret` into vault — must not be agent-accessible |
| List/inspect brokers (`GET /oauth-brokers`) | **Agent ✅** | `client_secret` is never included in the response |
| Generate connect link (`POST /oauth-brokers/{broker_id}/connect-link`) | **Agent ✅** | Generates a URL — no secret material involved |
| Sync connected accounts (`POST /oauth-brokers/{broker_id}/sync`) | **Agent ✅** | Pulls in tokens the human already approved — additive only |
| Delete / PATCH / reconnect | Human only | Destructive or credential-bearing |

### Where to see connected accounts in Pipedream

Connected accounts appear under your **project** in Pipedream, not your personal account settings:

1. Open your project in Pipedream
2. Click **Connect** in the left sidebar
3. Click the **Users** tab

You'll see your `external_user_id` (e.g. `frank`) with the connected app listed under it. These are project-scoped Connect accounts — separate from any personal accounts you've connected for your own Pipedream workflows.

---

## API Reference

### `POST /oauth-brokers/{broker_id}/connect-link`

Generate a one-time OAuth connect URL. Callable by agents (toolkit key) and human sessions.

**Request:**
```json
{
  "app": "google_drive",
  "external_user_id": "frank",
  "label": "Frank - Google Drive"
}
```

- `app`: **Required.** Pipedream app slug (e.g. `google_drive`, `gmail`, `slack`, `github`). Find slugs in [`src/brokers/pipedream.py`](../src/brokers/pipedream.py) or at [pipedream.com/apps](https://pipedream.com/apps).
- `external_user_id`: Your identifier for the user. Use `"default"` for single-user setups.
- `label`: Required — used to distinguish multiple accounts for the same app, since Pipedream only returns the app name (not the account email) at connect time.

You may also pass `api_id` (e.g. `"googleapis.com/drive"`) as optional metadata alongside `app`. If `api_id` is supplied and the slug map has an entry for it, the looked-up slug overrides the `app` you provided; otherwise your `app` value is used as-is.

**Response:**
```json
{
  "broker_id": "pipedream",
  "external_user_id": "frank",
  "app": "google_drive",
  "connect_link_url": "https://pipedream.com/_static/connect.html?token=ctok_...&app=google_drive",
  "expires_at": 1234567890,
  "next_step": "Visit connect_link_url in your browser, authorise google_drive, then call POST /oauth-brokers/{broker_id}/sync"
}
```

- `connect_link_url`: One-time URL — open in a browser to complete OAuth
- `expires_at`: Unix timestamp (seconds) when the link expires (~1 hour from generation)

---

### `POST /oauth-brokers/{broker_id}/sync`

After the user completes OAuth, pull the token into the local vault. Callable by agents (toolkit key) and human sessions.

**Request:**
```json
{
  "external_user_id": "frank"
}
```

**Response:**
```json
{
  "broker_id": "pipedream",
  "external_user_id": "frank",
  "accounts_synced": 1,
  "credentials": [
    {
      "id": "pipedream-apn_xxx-googleapis-com/drive",
      "label": "google_drive",
      "api_host": "googleapis.com/drive"
    }
  ],
  "next_step": "Provision a credential to a toolkit: POST /toolkits/{toolkit_id}/credentials with {credential_id}",
  "status": "ok"
}
```

After sync, bind the credential to a toolkit so agents can use it:
```bash
POST /toolkits/{toolkit_id}/credentials
{ "credential_id": "pipedream-apn_xxx-googleapis-com/drive" }
```

---

### `GET /oauth-brokers/{broker_id}/accounts`

List all accounts synced into this instance for the given broker.

```
GET /oauth-brokers/{broker_id}/accounts
GET /oauth-brokers/{broker_id}/accounts?external_user_id=frank
```

---

### `DELETE /oauth-brokers/{broker_id}/accounts/{account_id}`

Disconnect an account by its Pipedream account ID (`apn_xxx`). Removes the mapping from the local `oauth_broker_accounts` table, revokes the account on Pipedream's side, and removes the credential from the vault.

```
DELETE /oauth-brokers/pipedream/accounts/apn_abc123
```

Requires a human session. If the Pipedream revoke call fails, local cleanup still proceeds with a warning logged.

The `account_id` must be the Pipedream account ID (`apn_xxx`), not the API host — list `GET /oauth-brokers/{broker_id}/accounts` to find it.

---

## Supported Apps (70+)

The current `API_ID_TO_PD_SLUG` mapping in [`src/brokers/pipedream.py`](../src/brokers/pipedream.py) contains 70 entries across categories including Google (Gmail, Calendar, Drive, Sheets, Docs, Analytics, YouTube, Forms, Meet, Chat, BigQuery, Cloud Storage), Atlassian (Jira, Confluence), communication (Slack, Discord, Telegram, SendGrid, Mailchimp, Twilio), dev tools, CRM/sales, project management, storage, finance, analytics, productivity, support, AI, and music. See the map directly for the exact list and `api_id` keys — the doc here drifts fast.

Pipedream itself supports 3,000+ apps — if an app isn't in the slug map but exists in Pipedream, pass `app` directly (the Pipedream slug) and it will work. File a PR to add it to the mapping.

---

## Complete Example: Connecting Google Drive (agent-driven)

The agent uses its toolkit key throughout — no human login required after initial broker setup.

```bash
BASE="http://localhost:8900"
AGENT_KEY="tk_your-toolkit-key"
BROKER_ID="pipedream"

# 1. Agent generates a connect URL and surfaces it to the human
curl -s -X POST "$BASE/oauth-brokers/$BROKER_ID/connect-link" \
  -H "X-Jentic-API-Key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "app": "google_drive",
    "external_user_id": "frank",
    "label": "Frank - Google Drive (read-only)"
  }'
# → returns connect_link_url
# → human opens the URL in their browser and completes Google OAuth
# → human must be signed in to pipedream.com in the same browser (development mode)

# 2. Agent syncs the approved token into the vault
CRED_ID=$(curl -s -X POST "$BASE/oauth-brokers/$BROKER_ID/sync" \
  -H "X-Jentic-API-Key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"external_user_id": "frank"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['credentials'][0]['id'])")

echo "Credential stored: $CRED_ID"

# 3. Agent calls Google Drive via the broker — token injected automatically
curl -H "X-Jentic-API-Key: $AGENT_KEY" \
  "$BASE/googleapis.com/drive/v3/files?pageSize=10&orderBy=modifiedTime+desc"
```

---

## Token Refresh

Automatic token refresh on 401 is **not yet implemented** in the broker's `pipedream_oauth` handler (see `src/routers/broker.py`). The Pipedream platform access token that Jentic Mini uses to talk *to* Pipedream itself does auto-refresh — only the end-user OAuth tokens need manual re-sync on 401.

If you receive 401 errors on brokered calls, re-run sync to refresh:

```bash
POST /oauth-brokers/{broker_id}/sync
{ "external_user_id": "frank" }
```

---

## Pricing

- **Free in Pipedream's development environment** — unlimited usage

**Note on Pipedream pricing:** API calls are routed through Pipedream's Connect proxy — Pipedream injects the OAuth token server-side and forwards the request. This means calls count against Pipedream's proxy usage credits, not just the end-user count. See [Pipedream Connect pricing](https://pipedream.com/pricing?plan=Connect) for current credit costs.
