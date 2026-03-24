# Pipedream Connect Integration

Jentic Mini integrates with [Pipedream Connect](https://pipedream.com/connect) to provide OAuth authentication for 3,000+ SaaS apps — without implementing OAuth flows yourself or going through app certification with each platform.

## Why Pipedream Connect

OAuth is the auth standard used by every major SaaS platform (Gmail, Slack, Salesforce, GitHub, etc.). Implementing it properly requires:

- Registering OAuth clients with each platform
- Going through review/certification processes (Google, Slack, Salesforce all have this)
- Implementing the authorization code flow, token refresh, PKCE, etc.
- Handling token storage and rotation securely

Pipedream has done all of this for 3,000+ apps. Jentic Mini borrows that infrastructure: the user sees a Pipedream-hosted OAuth consent page, authorizes the app, and Pipedream stores the token. Jentic Mini then fetches the token and stores it in its local vault. All subsequent API calls go through the normal Jentic broker — Pipedream is only involved in the initial auth.

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

1. Open **[http://localhost:8900/oauth-brokers](http://localhost:8900/oauth-brokers)** in your browser
2. Log in with your Jentic Mini admin account if prompted
3. Click **Add Broker**
4. Fill in the form:
   - **Type:** `pipedream`
   - **Client ID:** your `client_id` from Step 2
   - **Client Secret:** your `client_secret` from Step 2
   - **Project ID:** your `project_id` from Step 3 (format: `proj_xxxxxxx`)
   - **Environment:** `development` (change to `production` when ready to go live)
5. Click **Save**

> **Development environment note:** Pipedream's `development` environment is free and supports all Connect features, but limits you to 10 external users and requires you to be signed in to pipedream.com in the same browser when completing OAuth flows.

---

## How It Works

Once the broker is registered, the connect and sync operations are **open to agents** — any valid toolkit key can call them. No human login step is required. The recommended approach is to let your agent drive the flow: it generates the connect URL and surfaces it to the human for a single click approval. The human never needs to interact with Jentic Mini directly.

```
1. Agent calls POST /oauth-brokers/pipedream/connect-link
   → Jentic Mini authenticates with Pipedream using your registered broker credentials
   → Pipedream mints a one-time connect token
   → Jentic Mini returns a connect URL (expires 4h)
   → Agent surfaces the URL to the human: "Click here to connect your Google Drive"

2. Human opens the URL in their browser
   → Must be signed in to pipedream.com (development environment requirement)
   → Sees Pipedream-hosted OAuth consent page for the target app
   → Completes OAuth (e.g. Google, Slack, GitHub)
   → Pipedream stores the access + refresh tokens under your project

3. Agent calls POST /oauth-brokers/pipedream/sync
   → Jentic Mini fetches the token from Pipedream and stores it in its local encrypted vault
   → From now on: normal Jentic broker handles all API calls
   → Pipedream is only contacted again for token refresh

4. (Automatic) Token refresh
   → If the broker gets a 401 from upstream, it fetches a fresh token from Pipedream
   → Vault is updated silently — the agent never sees the 401
```

You can also initiate connect-link manually via the Jentic Mini UI at `http://localhost:8900/oauth-brokers`, but letting the agent handle it is the recommended approach — it keeps the human interaction to a single OAuth approval click.

### Security boundary

| Operation | Who can call | Why |
|-----------|-------------|-----|
| Register broker (`POST /oauth-brokers`) | Human only | Injects `client_secret` into vault — must not be agent-accessible |
| List/inspect brokers (`GET /oauth-brokers`) | **Agent ✅** | `client_secret` is never included in the response |
| Generate connect link (`POST /oauth-brokers/{id}/connect-link`) | **Agent ✅** | Generates a URL — no secret material involved |
| Sync connected accounts (`POST /oauth-brokers/{id}/sync`) | **Agent ✅** | Pulls in tokens the human already approved — additive only |

### Where to see connected accounts in Pipedream

Connected accounts appear under your **project** in Pipedream, not your personal account settings:

1. Open your project in Pipedream
2. Click **Connect** in the left sidebar
3. Click the **Users** tab

You'll see your `external_user_id` (e.g. `frank`) with the connected app listed under it. These are project-scoped Connect accounts — separate from any personal accounts you've connected for your own Pipedream workflows.

---

## API Reference

### `POST /oauth-brokers/pipedream/connect-link`

Generate a one-time OAuth connect URL. Callable by agents (toolkit key) and human sessions.

**Request:**
```json
{
  "app": "google_drive",
  "external_user_id": "frank",
  "label": "Frank - Google Drive"
}
```

- `app`: Pipedream app slug (e.g. `google_drive`, `gmail`, `slack`, `github`). Find slugs via `GET /oauth-brokers/pipedream/apps` or at [pipedream.com/apps](https://pipedream.com/apps).
- `external_user_id`: Your identifier for the user. Use `"default"` for single-user setups.
- `label`: Required — used to distinguish multiple accounts for the same app, since Pipedream only returns the app name (not the account email) at connect time.

You may also pass `api_id` (e.g. `"googleapis.com/drive"`) instead of `app` — Jentic Mini will resolve it to the correct Pipedream slug automatically.

**Response:**
```json
{
  "broker_id": "pipedream",
  "external_user_id": "frank",
  "app": "google_drive",
  "connect_link_url": "https://pipedream.com/_static/connect.html?token=ctok_...&app=google_drive",
  "expires_at": "2026-03-24T15:16:25Z",
  "next_step": "Visit connect_link_url in your browser, authorise google_drive, then call POST /oauth-brokers/pipedream/sync"
}
```

Open `connect_link_url` in a browser to complete the OAuth flow.

---

### `POST /oauth-brokers/pipedream/sync`

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

### `GET /oauth-brokers/pipedream/accounts`

List all Pipedream-sourced accounts synced into this instance.

```
GET /oauth-brokers/pipedream/accounts
GET /oauth-brokers/pipedream/accounts?external_user_id=frank
```

---

### `DELETE /oauth-brokers/pipedream/accounts/{account_id}`

Disconnect an account (removes from local tracking, optionally deletes the credential).

```
DELETE /oauth-brokers/pipedream/accounts/apn_xyz123
DELETE /oauth-brokers/pipedream/accounts/apn_xyz123?delete_credential=false
```

Note: this does NOT revoke the token on Pipedream's side. Do that in the Pipedream dashboard if needed.

---

## Supported Apps (70+)

The current mapping covers:

| Category | Apps |
|----------|------|
| **Google** | Gmail, Calendar, Drive, Sheets, Docs, Analytics, YouTube, Forms, Meet, Chat, BigQuery, Cloud Storage |
| **Atlassian** | Jira, Confluence |
| **Communication** | Slack, Discord, Telegram, SendGrid, Mailchimp, Twilio |
| **Dev tools** | GitHub, GitLab, Bitbucket, Linear |
| **CRM / Sales** | HubSpot, Salesforce, Pipedrive, Close, Copper |
| **Project mgmt** | Asana, Trello, Monday, Notion, ClickUp, Airtable |
| **Storage** | Dropbox, Box, OneDrive |
| **Finance** | Stripe, Xero, QuickBooks, Braintree |
| **Social** | Twitter, Facebook, Instagram, LinkedIn |
| **Analytics** | Mixpanel, Segment, Amplitude |
| **Productivity** | Zoom, Calendly, Figma, Miro |
| **Support** | Intercom, Zendesk, Freshdesk |
| **AI** | OpenAI, Anthropic, Groq, Mistral, ElevenLabs |
| **Music** | Spotify |

To see the full list or check a specific app: `GET /oauth-brokers/pipedream/apps?q={name}`

Pipedream itself supports 3,000+ apps — if an app isn't in the slug map but exists in Pipedream, pass `app` directly (the Pipedream slug) and it will work. File a PR to add it to the mapping.

---

## Complete Example: Connecting Google Drive (agent-driven)

The agent uses its toolkit key throughout — no human login required after initial broker setup.

```bash
BASE="http://localhost:8900"
AGENT_KEY="tk_your-toolkit-key"

# 1. Agent generates a connect URL and surfaces it to the human
curl -s -X POST "$BASE/oauth-brokers/pipedream/connect-link" \
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
CRED_ID=$(curl -s -X POST "$BASE/oauth-brokers/pipedream/sync" \
  -H "X-Jentic-API-Key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"external_user_id": "frank"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['credentials'][0]['id'])")

echo "Credential stored: $CRED_ID"

# 3. Agent calls Google Drive via the broker — token injected automatically
curl -H "X-Jentic-API-Key: $AGENT_KEY" \
  "$BASE/www.googleapis.com/drive/v3/files?pageSize=10&orderBy=modifiedTime+desc"
```

---

## Token Refresh

Pipedream-sourced OAuth tokens expire (typically 1 hour for Google). Token refresh is handled automatically:

- When the broker forwards a request and gets a 401 from upstream
- If the credential is Pipedream-sourced (tracked in `pipedream_accounts`)
- The broker fetches a fresh token from Pipedream and updates the vault
- The request is retried — the agent never sees the 401

**Note:** The refresh hook is not yet wired into the broker — it's available as `src.routers.pipedream.refresh_pipedream_credential()`. Phase 2 work (see roadmap).

---

## Pricing

- **Free in Pipedream's development environment** — unlimited usage
- **Production**: billed per unique external user (we extract tokens directly and don't use Pipedream's proxy, so only the end-user count matters)
- For personal/single-user Jentic Mini: minimal cost (you're one external user)

See [Pipedream Connect pricing](https://pipedream.com/pricing?plan=Connect).
