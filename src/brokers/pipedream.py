"""
PipedreamOAuthBroker — OAuthBroker implementation backed by Pipedream Connect.

Pipedream has production OAuth app approvals for 3000+ SaaS APIs.
Rather than extracting raw tokens (which Pipedream only allows for user-supplied
OAuth clients, not their managed ones), we route requests through Pipedream's
Connect proxy — they inject the OAuth token server-side and forward verbatim.

Proxy URL shape:
  POST https://api.pipedream.com/v1/connect/{project_id}/proxy/{base64url(upstream_url)}
       ?external_user_id={id}&account_id={apn_xxx}
  Authorization: Bearer {pipedream_access_token}
  X-PD-Environment: production

Config is stored in the `oauth_brokers` DB table (not env vars).
The client_secret is Fernet-encrypted at rest.

Token cache: Pipedream access tokens expire in ~1 hour. We cache in memory
(per-instance) and refresh automatically.
"""
from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field

import httpx

from src.db import get_db
import src.vault as vault

log = logging.getLogger("jentic.brokers.pipedream")

# ── App slug ↔ api_id mapping ─────────────────────────────────────────────────
# Single authoritative map: Jentic canonical api_id → Pipedream app slug.
#
# Keys must match what _derive_api_id() produces from the API's servers[0].url:
#   - www. is stripped (googleapis.com/gmail not gmail.googleapis.com)
#   - version suffixes stripped (/v1, /v2, etc.)
#   - subdomain-only APIs stay as-is (api.github.com, slack.com/api, etc.)
#
# Used for:
#   1. Runtime credential lookup — broker resolves api_id → slug → account
#   2. Startup seeding — seed_broker_apps() in startup.py imports this map
#
# When the catalog key and the spec-derived id differ for a Google API, the
# catalog key (googleapis.com/<service>) wins — that's what _derive_api_id
# produces after stripping www.googleapis.com.
_API_ID_TO_PD_SLUG: dict[str, str] = {
    # Google — all served via www.googleapis.com; derive to googleapis.com/<svc>
    "googleapis.com/gmail":         "gmail",
    "googleapis.com/calendar":      "google_calendar",
    "googleapis.com/drive":         "google_drive",
    "googleapis.com/sheets":        "google_sheets",
    "googleapis.com/docs":          "google_docs",
    "googleapis.com/slides":        "google_slides",
    "googleapis.com/admin":         "google_admin",
    "googleapis.com/people":        "google_contacts",
    "googleapis.com/tasks":         "google_tasks",
    "googleapis.com/analytics":     "google_analytics",
    "googleapis.com/youtube":       "youtube",
    "googleapis.com/forms":         "google_forms",
    "googleapis.com/chat":          "google_chat",
    "googleapis.com/bigquery":      "google_bigquery",
    "googleapis.com/storage":       "google_cloud_storage",
    # Google — subdomain-native (not www.googleapis.com)
    "sheets.googleapis.com":        "google_sheets",
    "people.googleapis.com":        "google_contacts",
    # Atlassian
    "api.atlassian.com":            "jira",
    "atlassian.net":                "jira",
    # Communication
    "slack.com/api":                "slack",
    "discord.com/api":              "discord",
    "api.telegram.org":             "telegram_bot_api",
    "api.sendgrid.com":             "sendgrid",
    "api.mailchimp.com":            "mailchimp",
    "api.twilio.com":               "twilio",
    # Dev tools
    "api.github.com":               "github",
    "api.linear.app":               "linear_app",
    "api.vercel.com":               "vercel",
    "api.circleci.com":             "circleci",
    # CRM / sales
    "api.hubapi.com":               "hubspot",
    "api.salesforce.com":           "salesforce_rest_api",
    "salesforce.com":               "salesforce_rest_api",
    "api.pipedrive.com":            "pipedrive",
    "api.close.com":                "close",
    "api.intercom.io":              "intercom",
    # Project management
    "app.asana.com/api":            "asana",
    "api.trello.com":               "trello",
    "api.monday.com":               "monday",
    "api.notion.com":               "notion",
    "api.clickup.com":              "clickup",
    "api.airtable.com":             "airtable",
    # Storage / files
    "api.dropboxapi.com":           "dropbox",
    "api.box.com":                  "box",
    # Finance / payments
    "api.stripe.com":               "stripe",
    "api.xero.com":                 "xero",
    "platform.intuit.com":          "quickbooks",
    # Social / media
    "api.twitter.com":              "twitter",
    "api.x.com":                    "twitter",
    "graph.facebook.com":           "facebook",
    "api.linkedin.com":             "linkedin",
    "api.spotify.com":              "spotify",
    # Data / analytics
    "api.mixpanel.com":             "mixpanel",
    "api.segment.com":              "segment",
    "api.amplitude.com":            "amplitude",
    # Productivity
    "api.zoom.us":                  "zoom",
    "api.calendly.com":             "calendly",
    "api.figma.com":                "figma",
    "api.miro.com":                 "miro",
    "api.typeform.com":             "typeform",
    # Support
    "api.zendesk.com":              "zendesk",
    "zendesk.com":                  "zendesk",
    "api.freshdesk.com":            "freshdesk",
    "freshdesk.com":                "freshdesk",
    # E-commerce
    "api.shopify.com":              "shopify",
    "myshopify.com":                "shopify",
    # AI
    "api.openai.com":               "openai",
    "api.anthropic.com":            "anthropic",
    "api.groq.com/openai":          "groq",
    "api.mistral.ai":               "mistral",
    "api.elevenlabs.io":            "elevenlabs",
}

# Reverse: slug → list of api_hosts
_PD_SLUG_TO_HOSTS: dict[str, list[str]] = {}
for _host, _slug in _API_ID_TO_PD_SLUG.items():
    _PD_SLUG_TO_HOSTS.setdefault(_slug, []).append(_host)


def api_host_to_pd_slug(host: str) -> str | None:
    """Resolve an api host to a Pipedream app slug, or None."""
    if host in _API_ID_TO_PD_SLUG:
        return _API_ID_TO_PD_SLUG[host]
    # Partial match (e.g. subdomain)
    for pattern, slug in _API_ID_TO_PD_SLUG.items():
        if host.endswith(pattern) or pattern.endswith(host):
            return slug
    return None


def pd_slug_to_hosts(slug: str) -> list[str]:
    """Return all api_hosts that map to a given Pipedream app slug."""
    return _PD_SLUG_TO_HOSTS.get(slug, [])


# ── PipedreamOAuthBroker ──────────────────────────────────────────────────────

@dataclass
class PipedreamOAuthBroker:
    """OAuthBroker backed by Pipedream Connect proxy."""

    broker_id: str
    client_id: str
    client_secret: str          # decrypted at load time, never persisted
    project_id: str
    environment: str
    default_external_user_id: str

    # In-memory token cache (not persisted)
    _token_cache: str | None = field(default=None, repr=False)
    _token_expires_at: float = field(default=0.0, repr=False)

    # ── OAuthBroker protocol ──────────────────────────────────────────────────

    async def covers(self, api_host: str, external_user_id: str) -> bool:
        """Return True if we have a connected account for this host + user."""
        async with get_db() as db:
            async with db.execute(
                """SELECT 1 FROM oauth_broker_accounts
                   WHERE broker_id=? AND external_user_id=? AND api_host=? AND healthy=1""",
                (self.broker_id, external_user_id, api_host),
            ) as cur:
                return await cur.fetchone() is not None

    async def get_token(self, api_host: str, external_user_id: str) -> str | None:
        """Always returns None — Pipedream managed OAuth does not expose raw tokens.

        Requests must go through proxy_request() instead.
        """
        return None

    async def proxy_request(
        self,
        api_host: str,
        upstream_path: str,
        method: str,
        headers: dict,
        body: bytes,
        query_string: str,
        external_user_id: str,
    ) -> httpx.Response | None:
        """Route the request through Pipedream's Connect proxy.

        Pipedream injects the stored OAuth token server-side and forwards
        the request verbatim to the upstream API.
        """
        # Look up account_id for this host + user
        account_id = await self._get_account_id(api_host, external_user_id)
        if not account_id:
            log.warning(
                "PipedreamOAuthBroker: no account_id for host=%s user=%s",
                api_host, external_user_id,
            )
            return None

        # Build the full upstream URL (with query string if present)
        upstream_url = f"https://{api_host}{upstream_path}"
        if query_string:
            upstream_url += f"?{query_string}"

        # Base64url-encode the upstream URL (no padding)
        encoded_url = base64.urlsafe_b64encode(
            upstream_url.encode()
        ).rstrip(b"=").decode()

        proxy_url = (
            f"https://api.pipedream.com/v1/connect/{self.project_id}"
            f"/proxy/{encoded_url}"
            f"?external_user_id={external_user_id}&account_id={account_id}"
        )

        pd_token = await self._get_access_token()

        # Merge headers: Pipedream auth overrides, preserve Content-Type etc.
        proxy_headers = {k: v for k, v in headers.items()}
        proxy_headers["Authorization"] = f"Bearer {pd_token}"
        proxy_headers["X-PD-Environment"] = self.environment

        log.info(
            "PipedreamOAuthBroker proxy: %s %s → %s (account %s)",
            method, upstream_url, proxy_url[:80], account_id,
        )

        try:
            async with httpx.AsyncClient(timeout=35.0, follow_redirects=False) as client:
                response = await client.request(
                    method=method,
                    url=proxy_url,
                    headers=proxy_headers,
                    content=body if body else None,
                )
            return response
        except httpx.TimeoutException:
            log.warning("PipedreamOAuthBroker: proxy timeout for %s", upstream_url)
            return None
        except httpx.RequestError as exc:
            log.warning("PipedreamOAuthBroker: proxy error for %s: %s", upstream_url, exc)
            return None

    async def proxy_request_with_account(
        self,
        account_id: str,
        api_host: str,
        upstream_path: str,
        method: str,
        headers: dict,
        body: bytes,
        query_string: str,
        external_user_id: str = "default",
    ) -> httpx.Response | None:
        """Route through Pipedream proxy using a specific account_id.

        Bypasses the oauth_broker_accounts DB lookup — uses the account_id
        embedded in the provisioned credential directly. This is the path taken
        when a Pipedream credential has been explicitly provisioned to a toolkit.
        """
        upstream_url = f"https://{api_host}{upstream_path}"
        if query_string:
            upstream_url += f"?{query_string}"

        encoded_url = base64.urlsafe_b64encode(
            upstream_url.encode()
        ).rstrip(b"=").decode()

        proxy_url = (
            f"https://api.pipedream.com/v1/connect/{self.project_id}"
            f"/proxy/{encoded_url}"
            f"?external_user_id={external_user_id}&account_id={account_id}"
        )

        pd_token = await self._get_access_token()
        proxy_headers = {k: v for k, v in headers.items()}
        proxy_headers["Authorization"] = f"Bearer {pd_token}"
        proxy_headers["X-PD-Environment"] = self.environment

        log.info(
            "PipedreamOAuthBroker proxy (credential): %s %s → account %s",
            method, upstream_url, account_id,
        )

        try:
            async with httpx.AsyncClient(timeout=35.0, follow_redirects=False) as client:
                response = await client.request(
                    method=method,
                    url=proxy_url,
                    headers=proxy_headers,
                    content=body if body else None,
                )
            return response
        except httpx.TimeoutException:
            log.warning("PipedreamOAuthBroker: proxy timeout for %s", upstream_url)
            return None
        except httpx.RequestError as exc:
            log.warning("PipedreamOAuthBroker: proxy error for %s: %s", upstream_url, exc)
            return None

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        """Fetch (or return cached) Pipedream OAuth access token."""
        now = time.time()
        if self._token_cache and now < self._token_expires_at:
            return self._token_cache

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.pipedream.com/v1/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        token = data.get("access_token")
        if not token:
            raise ValueError(f"No access_token in Pipedream response: {data}")

        self._token_cache = token
        self._token_expires_at = now + 3500  # 1hr - 100s buffer
        log.debug("PipedreamOAuthBroker: refreshed access token for broker %s", self.broker_id)
        return token

    async def _get_account_id(self, api_host: str, external_user_id: str) -> str | None:
        """Look up the Pipedream account_id for a given host + user."""
        async with get_db() as db:
            async with db.execute(
                """SELECT account_id FROM oauth_broker_accounts
                   WHERE broker_id=? AND external_user_id=? AND api_host=?""",
                (self.broker_id, external_user_id, api_host),
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else None

    async def create_connect_token(self, external_user_id: str) -> dict:
        """Create a short-lived Pipedream Connect Token for the given user.

        Returns a dict with:
          - token: the connect token string
          - connect_link_url: the URL the user visits to connect apps
          - expires_at: Unix timestamp when the token expires
        """
        pd_token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.pipedream.com/v1/connect/{self.project_id}/tokens",
                headers={
                    "Authorization": f"Bearer {pd_token}",
                    "Content-Type": "application/json",
                    "X-PD-Environment": self.environment,
                },
                json={"external_user_id": external_user_id},
            )
            if resp.status_code != 200:
                raise ValueError(
                    f"Pipedream token creation failed ({resp.status_code}): {resp.text}"
                )
            data = resp.json()

        token = data.get("token")
        if not token:
            raise ValueError(f"No token in Pipedream response: {data}")

        # Pipedream returns the connect_link_url directly — use it verbatim
        connect_link_url = data.get("connect_link_url") or f"https://pipedream.com/_static/connect.html?token={token}&connectLink=true"
        expires_at = data.get("expires_at") or (time.time() + 3600)

        return {
            "token": token,
            "connect_link_url": connect_link_url,
            "expires_at": expires_at,
        }

    async def discover_accounts(self, external_user_id: str) -> int:
        """Fetch connected accounts from Pipedream, populate oauth_broker_accounts,
        and create/update credentials in the vault so they can be provisioned to toolkits.

        Calls Pipedream's /accounts endpoint, maps app slugs back to api_hosts,
        upserts rows, and writes a credential (scheme_name='pipedream_oauth') for
        each connected account. Labels come from oauth_broker_connect_labels if
        set at connect-link time; otherwise fall back to the app slug.

        Returns the count of account-host pairs discovered.
        """
        try:
            pd_token = await self._get_access_token()
        except Exception as exc:
            log.error("PipedreamOAuthBroker: can't get token for discovery: %s", exc)
            return 0

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"https://api.pipedream.com/v1/connect/{self.project_id}/accounts",
                    params={"external_user_id": external_user_id},
                    headers={
                        "Authorization": f"Bearer {pd_token}",
                        "X-PD-Environment": self.environment,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.warning("PipedreamOAuthBroker: discovery request failed: %s", exc)
            return 0

        accounts = data.get("accounts", data.get("data", []))
        count = 0

        async with get_db() as db:
            # Load pending labels: {app_slug: label}
            async with db.execute(
                "SELECT app_slug, label FROM oauth_broker_connect_labels "
                "WHERE broker_id=? AND external_user_id=?",
                (self.broker_id, external_user_id),
            ) as cur:
                pending_labels: dict[str, str] = {r[0]: r[1] for r in await cur.fetchall()}

            consumed_slugs: set[str] = set()

            for account in accounts:
                account_id = account.get("id", "")
                app_info = account.get("app", {})
                app_slug = app_info.get("name_slug", "") or app_info.get("slug", "")
                if not account_id or not app_slug:
                    continue

                label = pending_labels.get(app_slug, app_slug)

                hosts = pd_slug_to_hosts(app_slug)
                for api_host in hosts:
                    row_id = f"{self.broker_id}:{external_user_id}:{api_host}"
                    await db.execute(
                        """INSERT OR REPLACE INTO oauth_broker_accounts
                           (id, broker_id, external_user_id, api_host, app_slug,
                            account_id, label, healthy, synced_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                        (row_id, self.broker_id, external_user_id,
                         api_host, app_slug, account_id, label, time.time()),
                    )

                    # Upsert a credential in the vault so users can provision it to toolkits.
                    # Credential ID is stable: pipedream-{account_id}-{api_host_slug}
                    host_slug = api_host.replace(".", "-")
                    cred_id = f"pipedream-{account_id}-{host_slug}"
                    enc_account_id = vault.encrypt(account_id)
                    async with db.execute(
                        "SELECT id FROM credentials WHERE id=?", (cred_id,)
                    ) as cur:
                        exists = await cur.fetchone()

                    if exists:
                        # Update label and value in case either changed
                        await db.execute(
                            "UPDATE credentials SET label=?, encrypted_value=?, "
                            "api_id=?, scheme_name='pipedream_oauth', "
                            "updated_at=unixepoch() WHERE id=?",
                            (label, enc_account_id, api_host, cred_id),
                        )
                    else:
                        env_var = f"PIPEDREAM_{account_id.upper().replace('-', '_')}"
                        await db.execute(
                            "INSERT INTO credentials "
                            "(id, label, env_var, encrypted_value, api_id, scheme_name) "
                            "VALUES (?, ?, ?, ?, ?, 'pipedream_oauth')",
                            (cred_id, label, env_var, enc_account_id, api_host),
                        )

                    count += 1

                if app_slug in pending_labels:
                    consumed_slugs.add(app_slug)

            # Remove consumed pending labels
            for slug in consumed_slugs:
                await db.execute(
                    "DELETE FROM oauth_broker_connect_labels "
                    "WHERE broker_id=? AND external_user_id=? AND app_slug=?",
                    (self.broker_id, external_user_id, slug),
                )

            await db.commit()

        log.info(
            "PipedreamOAuthBroker: discovered %d account-host pairs for user=%s",
            count, external_user_id,
        )
        return count

    # ── Classmethod factory ───────────────────────────────────────────────────

    async def configure_project(
        self,
        app_name: str = "Jentic Mini",
        support_email: str | None = None,
        logo_url: str | None = None,
    ) -> None:
        """PATCH the Pipedream project with display name, support email, and logo.

        All three are optional — only non-None values are sent. Logo is fetched
        from logo_url and uploaded as a base64 data URL.
        """
        import base64
        import mimetypes

        pd_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {pd_token}",
            "Content-Type": "application/json",
        }
        base_url = f"https://api.pipedream.com/v1/connect/projects/{self.project_id}"

        patch_body: dict = {"app_name": app_name}
        if support_email:
            patch_body["support_email"] = support_email

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(base_url, json=patch_body, headers=headers)
            if resp.status_code not in (200, 204):
                log.warning(
                    "PipedreamOAuthBroker: project PATCH returned %s: %s",
                    resp.status_code, resp.text[:200],
                )
            else:
                log.info(
                    "PipedreamOAuthBroker: project configured (app_name=%r, support_email=%r)",
                    app_name, support_email,
                )

            if logo_url:
                try:
                    logo_resp = await client.get(logo_url, follow_redirects=True, timeout=10.0)
                    logo_resp.raise_for_status()
                    raw = logo_resp.content
                    mime = logo_resp.headers.get("content-type", "").split(";")[0].strip()
                    if not mime:
                        mime = mimetypes.guess_type(logo_url)[0] or "image/png"
                    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode()}"
                    logo_post = await client.post(
                        f"{base_url}/logo",
                        json={"logo": data_url},
                        headers=headers,
                    )
                    if logo_post.status_code not in (200, 204):
                        log.warning(
                            "PipedreamOAuthBroker: logo upload returned %s: %s",
                            logo_post.status_code, logo_post.text[:200],
                        )
                    else:
                        log.info("PipedreamOAuthBroker: logo uploaded from %s", logo_url)
                except Exception as exc:
                    log.warning("PipedreamOAuthBroker: logo upload failed: %s", exc)


    @classmethod
    async def from_db(cls) -> list["PipedreamOAuthBroker"]:
        """Load all Pipedream broker configs from DB and return instances."""
        async with get_db() as db:
            async with db.execute(
                "SELECT id, client_id, client_secret_enc, project_id, "
                "environment, default_external_user_id FROM oauth_brokers WHERE type='pipedream'"
            ) as cur:
                rows = await cur.fetchall()

        brokers = []
        for row in rows:
            broker_id, client_id, client_secret_enc, project_id, environment, default_ext_uid = row
            try:
                client_secret = vault.decrypt(client_secret_enc)
            except Exception as exc:
                log.error(
                    "PipedreamOAuthBroker: failed to decrypt secret for broker %s: %s",
                    broker_id, exc,
                )
                continue
            brokers.append(cls(
                broker_id=broker_id,
                client_id=client_id,
                client_secret=client_secret,
                project_id=project_id,
                environment=environment or "production",
                default_external_user_id=default_ext_uid or "default",
            ))

        log.info("PipedreamOAuthBroker: loaded %d broker(s) from DB", len(brokers))
        return brokers
