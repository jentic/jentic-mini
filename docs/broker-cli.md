# Using the Broker with CLI Tools

The Jentic Mini broker (`/{upstream_host}/{path}`, any HTTP method) is an HTTP
proxy that injects authentication credentials on behalf of a caller. Any CLI
tool that speaks HTTP can use it — not just agents.

This is useful when you want CLI tools like `git`, `curl`, `aws`, or `stripe`
to make authenticated requests **without embedding credentials in your shell
environment or config files**. Credentials stay in the vault; the broker
injects them at request time.

---

## How it Works

The broker URL shape is:

```
http://<jentic-mini-host>/<upstream-host>/<path>
```

For example, to proxy a request to `https://api.github.com/repos/org/repo`:

```
http://localhost:8900/api.github.com/repos/org/repo
```

The broker:
1. Looks up the API registered under the upstream hostname
2. Selects the matching credential from your toolkit
3. Injects auth headers (Bearer, BasicAuth, ApiKey, etc.) before forwarding
4. Returns the upstream response verbatim

Request headers the broker reads:

| Header | Purpose |
|--------|---------|
| `X-Jentic-API-Key` | Authenticates the caller and selects the toolkit (required for credential injection) |
| `X-Jentic-Credential` | Selects a specific credential by ID (optional; hard override) |
| `X-Jentic-Service` | Selects by service name, e.g. `google_calendar` (optional; friendlier than `X-Jentic-Credential`) |
| `X-Jentic-Simulate` | Set to `true` to dry-run — returns what would be sent upstream without making the call |

Response headers the broker sets:

| Header | Meaning |
|--------|---------|
| `X-Jentic-Execution-Id` | Trace ID for this request (look up in `GET /traces`) |
| `X-Jentic-Credential-Used` | ID of the credential that was injected |
| `X-Jentic-Credential-Ambiguous` | `true` if multiple credentials matched and none was explicitly selected (returned with HTTP 409) |

---

## git over HTTPS

Git speaks plain HTTPS — it can route through the broker by setting a custom
remote URL and injecting extra headers via `git config`.

### Setup

```bash
# Add a brokered remote
git remote add upstream-brokered \
  http://localhost:8900/github.com/org/repo.git

# Inject your toolkit key
git config \
  http.http://localhost:8900/github.com/org/repo.git.extraHeader \
  "X-Jentic-API-Key: tk_your_toolkit_key"

# Optionally pin a specific credential
git config \
  http.http://localhost:8900/github.com/org/repo.git.extraHeader \
  "X-Jentic-Credential: github.com-my-pat"
```

> **Note:** `git config` only stores one value per key, so the second
> `extraHeader` overwrites the first. Set both headers in the same call
> using `git config --add` for the second:
>
> ```bash
> git config \
>   http.http://localhost:8900/github.com/org/repo.git.extraHeader \
>   "X-Jentic-API-Key: tk_your_toolkit_key"
> git config --add \
>   http.http://localhost:8900/github.com/org/repo.git.extraHeader \
>   "X-Jentic-Credential: github.com-my-pat"
> ```

### Push / Pull

```bash
git push upstream-brokered main
git pull upstream-brokered main
```

### GitHub BasicAuth encoding

GitHub's git-over-HTTPS requires BasicAuth. The wire format is:

```
Authorization: Basic base64("<username>:<PAT>")
```

GitHub accepts any non-empty string as the username — `token`, `x-access-token`,
your actual username, all work. Jentic Mini uses `token` as the default when no
`identity` is set on the credential.

To use a specific username, set `identity` when creating or patching the credential:

```bash
curl -s -X PATCH http://localhost:8900/credentials/github-com-my-pat \
  -H "X-Jentic-API-Key: tk_your_toolkit_key" \
  -H "Content-Type: application/json" \
  -d '{"identity": "token"}'
```

For most users this is unnecessary — the default `token` username works fine with GitHub.

See [credentials.md](credentials.md) for how to add the PAT credential.

---

## curl

```bash
# Proxy any HTTP request through the broker
curl -s http://localhost:8900/api.github.com/repos/org/repo \
  -H "X-Jentic-API-Key: tk_your_toolkit_key"

# Pin a specific credential
curl -s http://localhost:8900/api.github.com/user \
  -H "X-Jentic-API-Key: tk_your_toolkit_key" \
  -H "X-Jentic-Credential: github.com-my-pat"
```

---

## Simulate mode

Add the `X-Jentic-Simulate: true` header to any broker request to return what
would be sent upstream without making the call. Useful for debugging credential
selection:

```bash
curl -s "http://localhost:8900/api.github.com/user" \
  -H "X-Jentic-API-Key: tk_your_toolkit_key" \
  -H "X-Jentic-Credential: github.com-my-pat" \
  -H "X-Jentic-Simulate: true"
```

Response:
```json
{
  "simulate": true,
  "synthesised": false,
  "valid": true,
  "would_send": {
    "method": "GET",
    "url": "https://api.github.com/user",
    "headers": {
      "Authorization": "***"
    }
  }
}
```

Authorization-bearing headers are masked as `"***"` in the response.

---

## Credential selection logic

When the broker receives a request for `host`:

1. Looks up credentials bound to your toolkit that match the host + path via the `credential_routes` table.
2. If `X-Jentic-Credential` is set, selects the credential matching that ID (hard override). If `X-Jentic-Service` is set, selects by service name.
3. If neither is set and exactly one credential matches, uses it.
4. If multiple credentials match with no hint, returns **HTTP 409 `CREDENTIAL_AMBIGUOUS`** and sets the `X-Jentic-Credential-Ambiguous: true` response header — the caller must supply `X-Jentic-Credential` or `X-Jentic-Service`.
5. Resolves the security scheme from the API spec plus any confirmed overlays.
6. Injects the auth header and forwards the request.

**Unauthenticated requests** (no `X-Jentic-API-Key`) are forwarded as-is without credential injection — the upstream decides. **Authenticated requests with no matching credential** are denied with HTTP 403 `policy_denied`.

If BasicAuth is selected, the broker constructs `Authorization: Basic base64("{identity ?? 'token'}:{value}")`. If the credential's `value` already contains a `:` (e.g. you stored `user:pass`), it is used verbatim without prepending `identity`. Set `identity` on the credential when the API requires a specific username.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 403 from upstream | Wrong credential selected | Add `X-Jentic-Service: google_calendar` (or `X-Jentic-Credential`) to select the right one |
| 400 from GitHub git push | Wrong BasicAuth encoding | Check the `identity` field on the credential — should be `token` or any non-empty string |
| No auth injected | Credential not bound to toolkit | `POST /toolkits/{id}/credentials` |
| No auth injected | API has no security scheme | Submit an overlay via `POST /apis/{api_id}/overlays` |
| Credential alias ignored | Credential not found by alias | Check alias matches the credential ID/label in the vault |
