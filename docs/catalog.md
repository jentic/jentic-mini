# Public Catalog Integration

Jentic Mini is connected to the **Jentic public API catalog** — an open-source repository of OpenAPI specs and Arazzo workflows maintained at [github.com/jentic/jentic-public-apis](https://github.com/jentic/jentic-public-apis).

The catalog contains ~1,044 individual API specs and ~380 workflow sources. Jentic Mini surfaces these alongside your locally registered APIs in every endpoint — no manual import required.

---

## How It Works

### Lazy manifest (zero network cost at query time)

Jentic Mini does **not** clone the entire public catalog repo. Instead it:

1. Fetches the full recursive git tree from the GitHub API in 2 HTTP calls (~1–2 MB JSON)
2. Builds a local manifest (`data/catalog_manifest.json` and `data/workflow_manifest.json`)
3. Caches the manifests for 24 hours

All search, list, and dedup operations run against the local manifests — no GitHub calls are made during normal API use.

When a spec or workflow is actually needed (import, execution), it is fetched on demand from GitHub raw.

### Umbrella vendor expansion

Many vendors host multiple distinct APIs under a single domain (e.g. `googleapis.com` has `gmail`, `calendar`, `maps`, `sheets`, ...). The manifest refresh detects these "umbrella" vendors and expands them one level deeper:

- `googleapis.com` → `googleapis.com/gmail`, `googleapis.com/calendar`, `googleapis.com/maps`, ... (200+ entries)
- `atlassian.com` → `atlassian.com/jira`, `atlassian.com/confluence`, ...
- `adyen.com` → `adyen.com/AccountService`, `adyen.com/PaymentService`, ...

Single-product vendors (e.g. `stripe.com`, `twilio.com`) remain as flat entries.

### Vendor-aware deduplication

Catalog entries that are already in your local registry are hidden from list/search results. The dedup logic is vendor-aware:

- **Sub-API match**: `language.googleapis.com` locally registered → hides `googleapis.com/language` from catalog, but NOT `googleapis.com/gmail` or `googleapis.com/calendar`
- **Leaf vendor match**: `api.stripe.com` locally registered → hides leaf `stripe.com` catalog entry (same underlying vendor, generic `api.` subdomain)
- **Generic subdomains** (`api.`, `www.`, `app.`, `portal.`) are treated as vendor-level entries, not product-specific

---

## Refreshing the Manifest

The manifest is refreshed automatically at startup if absent or older than 24 hours. To force a refresh:

```http
POST /catalog/refresh
X-Jentic-API-Key: {admin_key}
```

Response:
```json
{
  "status": "ok",
  "api_entries": 1044,
  "workflow_sources": 380,
  "method": "tree",
  "fetched_at": 1742234155.29
}
```

`method` will be `"tree"` (full expansion via GitHub tree API) or `"shallow_fallback"` (flat domain listing, used if the tree API response is truncated).

---

## Browsing the Catalog

### APIs — merged with local registry

`GET /apis` always returns both local and catalog APIs in a single merged list:

```http
GET /apis?q=stripe&limit=10
X-Jentic-API-Key: {key}
```

Each result includes a `source` field:

```json
{
  "data": [
    {
      "id": "api.stripe.com",
      "name": "api.stripe.com",
      "source": "local",
      "has_credentials": true,
      "vendor": "stripe.com",
      "_links": { ... }
    },
    {
      "id": "googleapis.com/gmail",
      "name": "googleapis.com/gmail",
      "source": "catalog",
      "has_credentials": false,
      "vendor": "googleapis.com",
      "_links": {
        "catalog": "/catalog/googleapis.com/gmail",
        "github": "https://github.com/jentic/jentic-public-apis/tree/main/apis/openapi/googleapis.com/gmail"
      }
    }
  ],
  "total": 1066
}
```

Filter by source:
- `?source=local` — only locally registered APIs
- `?source=catalog` — only catalog APIs not yet in your registry

### Workflows — merged with local registry

`GET /workflows` returns both locally imported workflows and catalog workflow sources:

```http
GET /workflows?q=slack
```

```json
[
  {
    "slug": "post-slack-message",
    "name": "Post a Slack message",
    "source": "local",
    "steps_count": 2,
    "involved_apis": ["slack.com"]
  },
  {
    "slug": "slack.com",
    "name": "slack.com (catalog)",
    "source": "catalog",
    "description": "Workflows available from the Jentic public catalog for slack.com. Add credentials for this API to import them automatically.",
    "involved_apis": ["slack.com"],
    "_links": {
      "catalog_api": "/catalog/slack.com",
      "add_credentials": "/credentials",
      "github": "https://github.com/jentic/jentic-public-apis/tree/main/workflows/slack.com"
    }
  }
]
```

Filter: `?source=local|catalog`, `?q=<text>`

### Catalog detail

Inspect a specific catalog entry before importing:

```http
GET /catalog/googleapis.com/gmail
X-Jentic-API-Key: {key}
```

Returns spec metadata, available auth schemes, and a link to the raw spec on GitHub.

### Search — blended results

`GET /search` blends catalog APIs and workflow sources into results alongside local operations and workflows:

```http
GET /search?q=send+email&n=10
```

Results include `source` field. Catalog results link to `/catalog/{api_id}` and `GET /credentials` for next steps.

---

## Importing from the Catalog

### Automatic import on credential add (recommended)

The simplest flow: just add your credentials for a catalog API. Jentic Mini will automatically:

1. Detect that the API is catalog-only (not yet in your local registry)
2. Fetch the OpenAPI spec from GitHub and register it
3. Fetch the Arazzo workflow file from GitHub
4. Rewrite `sourceDescriptions` URLs in the workflow to point to your local spec copy
5. Save and register all workflows from that source (e.g. Slack has 17 workflows)

```http
POST /credentials
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "api_id": "slack.com",
  "scheme_name": "BearerAuth",
  "values": { "token": "xoxb-..." }
}
```

After this single call:
- `GET /apis?source=local` — slack.com appears
- `GET /workflows?source=local&q=slack` — 17 Slack workflows appear, ready to execute

### What gets imported per API

- **API spec**: saved to `/app/src/specs/<api_id>.json`, registered in the `apis` table
- **Workflows**: each workflow from the source's `workflows.arazzo.json` saved as a separate file (`catalog_<source_id>_<workflow_id>.json`), registered in the `workflows` table. The `sourceDescriptions` are rewritten to use your local spec path.

The import is **idempotent** — adding credentials again will not create duplicates.

### Manual refresh (catalog endpoint)

While automatic import via `POST /credentials` is the recommended flow, you can also trigger a catalog refresh directly:

```http
POST /catalog/refresh
X-Jentic-API-Key: {admin_key}
```

---

## Catalog Repository Structure

The public catalog lives at `github.com/jentic/jentic-public-apis`:

```
jentic-public-apis/
├── apis/
│   └── openapi/
│       ├── stripe.com/
│       │   └── main/1.0/openapi.json          # leaf API
│       ├── googleapis.com/
│       │   ├── gmail/main/1.0/openapi.json    # umbrella sub-API
│       │   ├── calendar/main/v3/openapi.json
│       │   └── maps/...
│       └── atlassian.com/
│           ├── jira/main/v3/openapi.json
│           └── confluence/...
└── workflows/
    ├── stripe.com/
    │   └── workflows.arazzo.json              # contains 7 workflows
    ├── slack.com/
    │   └── workflows.arazzo.json              # contains 17 workflows
    └── atlassian.com~jira/                    # ~ separates vendor from sub-API
        └── workflows.arazzo.json              # contains 10 workflows
```

Key naming conventions:
- **APIs**: umbrella vendors use subdirectories (`googleapis.com/gmail/`); leaf vendors are flat (`stripe.com/`)
- **Workflows**: the `~` character separates vendor from sub-API in directory names (`atlassian.com~jira` = API `atlassian.com/jira`)
- Each `workflows.arazzo.json` may contain multiple workflow definitions

---

## API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /catalog/refresh` | Fetch latest manifest from GitHub. Auto-runs on startup if stale. |
| `GET /catalog` | Browse catalog entries. Supports `?q=` search. |
| `GET /catalog/{api_id}` | Inspect a specific catalog entry (spec metadata, auth schemes, GitHub link). |
| `GET /apis` | List APIs — local + catalog merged. `?source=local\|catalog`, `?q=`. |
| `GET /workflows` | List workflows — local + catalog merged. `?source=local\|catalog`, `?q=`. |
| `GET /search` | Full-text search — blends local ops/workflows with catalog APIs/workflow sources. |
| `POST /credentials` | Add credentials. If `api_id` is catalog-only, auto-imports spec + workflows first. |

---

## Counts (as of last manifest refresh)

| Resource | Count |
|----------|-------|
| API entries in catalog | 1,044 |
| Workflow sources in catalog | 380 |
| Umbrella vendors expanded | ~89 (e.g. googleapis.com → 270+ sub-APIs) |

---

## Differences from Jentic Hosted

The Jentic hosted and VPC editions offer a richer catalog experience:

| Feature | Jentic Mini | Jentic Hosted / VPC |
|---------|------------|---------------------|
| Catalog size | ~1,044 APIs, ~380 workflow sources | Central catalog — aggregates collective agent knowledge |
| Search | BM25 substring | Semantic search (~64% accuracy improvement) |
| Manifest refresh | GitHub tree API (2 calls) | Managed, versioned, real-time |
| Import | On credential add (lazy) | Pre-warmed, instant |
| Catalog contributions | Manual PR to jentic-public-apis | Built-in `POST /catalog/{api_id}/contribute` |
