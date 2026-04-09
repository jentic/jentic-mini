# Using the Broker with CLI Tools

The Jentic Mini broker (`POST /broker/{host}/{path}`) is an HTTP proxy that
injects authentication credentials on behalf of a caller. Any CLI tool that
speaks HTTP can use it — not just agents.

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

Two request headers control credential selection:

| Header | Purpose |
|--------|---------|
| `X-Jentic-API-Key` | Selects your toolkit (required) |
| `X-Jentic-Credential` | Selects a specific credential by ID/slug (optional; hard override) |

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

See [CREDENTIALS.md](CREDENTIALS.md) for how to add the PAT credential.

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

Add `?simulate=true` to any broker request to return what headers *would* be
injected without making the upstream call. Useful for debugging credential
selection:

```bash
curl -s "http://localhost:8900/api.github.com/user?simulate=true" \
  -H "X-Jentic-API-Key: tk_your_toolkit_key" \
  -H "X-Jentic-Credential: github.com-my-pat"
```

Response:
```json
{
  "simulate": true,
  "target_url": "https://api.github.com/user",
  "injected_headers": {
    "Authorization": "Basic eC1hY2Nlc3MtdG9rZW46..."
  }
}
```

---

## Credential selection logic

When the broker receives a request for `host`:

1. Looks up all credentials bound to your toolkit for that `api_id`
2. If `X-Jentic-Credential` is set, selects the credential matching that alias
3. Otherwise, picks the first credential registered for the host
4. Resolves the security scheme from the API spec or any registered overlay
5. Injects auth headers and forwards the request

If no credential is found, the request is forwarded unauthenticated.

If BasicAuth is selected, the broker constructs:
`Authorization: Basic base64("{identity ?? 'token'}:{value}")`.
Set `identity` on the credential if the API requires a specific username.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 403 from upstream | Wrong credential selected | Add `X-Jentic-Credential: work-gmail` to select the right one, or update credential `routes` |
| 400 from GitHub git push | Wrong BasicAuth encoding | Check the `identity` field on the credential — should be `token` or any non-empty string |
| No auth injected | Credential not bound to toolkit | `POST /toolkits/{id}/credentials` |
| No auth injected | API has no security scheme | Submit an overlay via `POST /apis/{api_id}/overlays` |
| Credential alias ignored | Credential not found by alias | Check alias matches the credential ID/label in the vault |
