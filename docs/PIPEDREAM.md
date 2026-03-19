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

1. **Create a Pipedream account** at [pipedream.com](https://pipedream.com) (free)
2. **Create a project** in the Pipedream dashboard
3. **Create an OAuth client** in your project's Settings → OAuth Clients
4. **Copy your credentials**:
   - `client_id`
   - `client_secret`
   - `project_id` (shown in project Settings)
5. **Set environment variables** for Jentic Mini:

```bash
PIPEDREAM_CLIENT_ID=your_client_id
PIPEDREAM_CLIENT_SECRET=your_client_secret
PIPEDREAM_PROJECT_ID=your_project_id
PIPEDREAM_ENVIRONMENT=development  # change to "production" when ready
```

In Docker Compose, add these to the `environment:` section. Hot reload applies — no restart needed once set.

---

## How It Works

```
1. POST /connect/link
   → Jentic Mini calls Pipedream: "create a connect token for user X, app Y"
   → Returns a one-time URL (expires 4h or after first use)

2. User opens the URL in their browser
   → Sees Pipedream-hosted OAuth page for the app (e.g. "Connect Gmail")
   → Completes Google/Slack/GitHub OAuth
   → Pipedream stores the access + refresh tokens

3. POST /connect/sync
   → Jentic Mini calls Pipedream: "give me the token for user X, app Y"
   → Token is extracted and stored in Jentic Mini's encrypted credential vault
   → From now on: normal Jentic broker handles all API calls

4. (Automatic) Token refresh
   → If the broker gets a 401 from upstream, it calls Pipedream to get a fresh token
   → Vault is updated silently — the agent never sees the 401
```

---

## API Reference

### `POST /connect/link`

Generate a one-time OAuth connect URL. Requires human session.

**Request:**
```json
{
  "app": "gmail",
  "external_user_id": "sean"
}
```

Or use `api_id` instead of `app` — Jentic Mini auto-resolves to the Pipedream slug:
```json
{
  "api_id": "gmail.googleapis.com",
  "external_user_id": "sean"
}
```

**Response:**
```json
{
  "connect_url": "https://pipedream.com/connect/abc123?app=gmail",
  "token": "abc123...",
  "app_slug": "gmail",
  "external_user_id": "sean",
  "expires_in": 14400
}
```

Open `connect_url` in a browser to complete the OAuth flow.

---

### `POST /connect/sync`

After the user completes OAuth, pull the token into the local vault. Requires human session.

**Request:**
```json
{
  "app": "gmail",
  "external_user_id": "sean"
}
```

**Response:**
```json
{
  "status": "ok",
  "api_id": "gmail.googleapis.com",
  "app_slug": "gmail",
  "credential_id": "a1b2c3d4-...",
  "account_id": "apn_xyz123",
  "external_user_id": "sean",
  "scheme_name": "oauth2",
  "message": "Token stored in vault as credential 'a1b2c3d4-...'. Bind it to a toolkit via POST /toolkits/{id}/credentials to use it."
}
```

After sync, bind the credential to a toolkit so agents can use it:
```bash
POST /toolkits/{toolkit_id}/credentials
{ "credential_id": "a1b2c3d4-..." }
```

---

### `GET /connect/accounts`

List all Pipedream-sourced accounts synced into this instance.

```
GET /connect/accounts
GET /connect/accounts?external_user_id=sean
GET /connect/accounts?app=gmail
```

---

### `GET /connect/apps`

List all apps with Pipedream integration support, with their Jentic api_id mapping.

```
GET /connect/apps
GET /connect/apps?q=google
GET /connect/apps?q=slack
```

---

### `DELETE /connect/accounts/{account_id}`

Disconnect an account (removes from local tracking, optionally deletes the credential).

```
DELETE /connect/accounts/apn_xyz123
DELETE /connect/accounts/apn_xyz123?delete_credential=false
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

To see the full list or check a specific app: `GET /connect/apps?q={name}`

Pipedream itself supports 3,000+ apps — if an app isn't in the slug map but exists in Pipedream, pass `app` directly (the Pipedream slug) and it will work. File a PR to add it to the mapping.

---

## Complete Example: Connecting Gmail

```bash
ADMIN_KEY="your-jentic-mini-admin-key"
BASE="https://jentic-mini.home.seanblanchfield.com"

# 1. Generate connect URL
LINK=$(curl -s -X POST "$BASE/connect/link" \
  -H "X-Jentic-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"api_id": "gmail.googleapis.com", "external_user_id": "sean"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['connect_url'])")

echo "Open this in your browser: $LINK"

# 2. (User opens $LINK, completes Gmail OAuth)

# 3. Sync the token into the vault
CRED_ID=$(curl -s -X POST "$BASE/connect/sync" \
  -H "X-Jentic-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"api_id": "gmail.googleapis.com", "external_user_id": "sean"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['credential_id'])")

echo "Credential stored: $CRED_ID"

# 4. Bind to a toolkit
curl -s -X POST "$BASE/toolkits/default/credentials" \
  -H "X-Jentic-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"credential_id\": \"$CRED_ID\"}"

# 5. Now agents can call Gmail via the broker:
curl -X GET "https://gmail.googleapis.com/gmail/v1/users/me/profile" \
  -H "X-Jentic-API-Key: your-toolkit-key"
# → broker injects Bearer token automatically
```

---

## Token Refresh

Pipedream-sourced OAuth tokens expire (typically 1 hour for Google). Token refresh is handled automatically:

- When the broker forwards a request and gets a 401 from upstream
- If the credential is Pipedream-sourced (tracked in `pipedream_accounts`)
- The broker calls `refresh_pipedream_credential()` which fetches a fresh token from Pipedream
- The vault is updated and the request is retried

**Note:** The refresh hook is not yet wired into the broker — it's available as `src.routers.pipedream.refresh_pipedream_credential()`. Phase 2 work (see roadmap).

---

## Pricing

- **Free in Pipedream's development environment** — unlimited usage
- **Production**: billed per unique external user + credits for proxy usage (we don't use the proxy — we extract tokens directly, so only the end-user count matters)
- For personal/single-user Jentic Mini: minimal cost (you're one external user)

See [Pipedream Connect pricing](https://pipedream.com/pricing?plan=Connect).
