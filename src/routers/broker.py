"""
Broker — transparent HTTP reverse proxy with credential injection.

URL pattern: /{upstream_host}/{path}
  e.g. POST /api.stripe.com/v1/payment_intents
       GET  /api.github.com/repos/octocat/Hello-World

The broker:
  1. Detects the upstream host from the first path segment (must contain a ".")
  2. Looks up the credential for that host in the vault (toolkit-scoped if
     a toolkit API key was used, otherwise global)
  3. Injects the credential into the forwarded request headers
  4. Forwards the request verbatim (method, headers, body, query params)
  5. Returns the upstream response verbatim — no wrapping

Special request headers:
  X-Jentic-API-Key    — Jentic authentication (handled by auth middleware)
  X-Jentic-Simulate   — "true" to skip the upstream call and return would_send
  X-Jentic-Credential — credential alias; acts as a HARD OVERRIDE — the named
                        credential is used for both policy enforcement and injection,
                        bypassing host-matching auto-selection entirely. Required when
                        multiple credentials share the same upstream host (e.g. multiple
                        Google services all routing through googleapis.com).
  X-Jentic-Service    — service name (Pipedream app_slug, e.g. "google_calendar") to
                        select the right credential when multiple share a host.
                        Friendlier alternative to X-Jentic-Credential.
  X-Jentic-Callback   — webhook URL for async result delivery (TODO: phase 2)

Response headers added:
  X-Jentic-Error              — "true" when the error is from Jentic, not upstream
  X-Jentic-Execution-Id       — trace ID (exec_*) for this broker call
  X-Jentic-Credential-Used    — ID of the credential actually injected (always set when
                                a credential was used, enabling callers to detect wrong-
                                credential selection on multi-service hosts)
  X-Jentic-Credential-Ambiguous — "true" when multiple credentials matched and no
                                  alias/service was specified to disambiguate
"""
import json
import logging
import time
import asyncio
from typing import Annotated, Optional
from urllib.parse import unquote, urlparse

import httpx
from fastapi import APIRouter, Path, Request, Response, HTTPException
from fastapi.routing import APIRoute

log = logging.getLogger("jentic.broker")

from jentic.apitools.openapi.common.uri import is_http_https_url
from src.config import JENTIC_PUBLIC_HOSTNAME
from src.db import get_db
from src.routers.credentials import api_has_native_scheme
import src.vault as vault
from src.routers.traces import new_trace_id, safe_write_trace
from src.openapi_helpers import agent_hints
# Lazy import to avoid circular deps — imported inline where needed
# from src.routers.workflows import dispatch_workflow

router = APIRouter(tags=["execute"])


class ServiceNotFoundError(Exception):
    """Raised when X-Jentic-Service doesn't match any credential for the host."""


# Hop-by-hop headers that must NOT be forwarded
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    # httpx decompresses automatically — forwarding Content-Encoding causes
    # ERR_CONTENT_DECODING_FAILED in browsers because content is already decoded
    "content-encoding",
    # Content-Length from upstream is wrong after decompression; let ASGI recalculate
    "content-length",
    # Jentic-specific — consumed here, not forwarded upstream
    "x-jentic-api-key", "x-jentic-simulate",
    "x-jentic-credential", "x-jentic-service", "x-jentic-callback",
    # Host is set from the target URL
    "host",
    # Reverse-proxy headers injected by nginx/traefik/etc. — these describe
    # the inbound hop to Jentic, not the outbound hop to the upstream API.
    # Forwarding them causes failures: e.g. CloudFront returns 403
    # "Host not permitted" when it sees x-forwarded-host with the Jentic
    # hostname instead of the upstream API hostname.
    "x-forwarded-for", "x-forwarded-host", "x-forwarded-port",
    "x-forwarded-proto", "x-forwarded-scheme",
    "x-real-ip", "x-scheme",
}

# How we detect credentials for a given API host
# Looks up the api in the apis table by id (which is the scheme-stripped base URL)
# then finds matching credentials by api_id + auth_type and injects them as HTTP headers.
async def _resolve_credential_ids(host: str, toolkit_id: str | None) -> tuple[str | None, list[str]]:
    """Resolve host → (api_id, [credential_ids]) without decrypting anything.
    Used for policy checks before the vault is touched.
    """
    candidates = [host]
    parts = host.split(".")
    if len(parts) > 2:
        candidates.append(".".join(parts[1:]))

    api_id = None
    async with get_db() as db:
        for candidate in candidates:
            # ORDER BY length(id) DESC ensures longest (most specific) match wins,
            # making selection deterministic when multiple APIs share a host prefix
            # (e.g. googleapis.com/calendar vs googleapis.com/gmail).
            async with db.execute(
                "SELECT id FROM apis WHERE id=? OR id LIKE ? ORDER BY length(id) DESC LIMIT 1",
                (candidate, f"{candidate}%"),
            ) as cur:
                row = await cur.fetchone()
            if row:
                api_id = row[0]
                break

    if not api_id or not toolkit_id:
        return api_id, []

    cred_ids = await vault.get_credential_ids_for_api(toolkit_id, api_id)
    return api_id, cred_ids


async def _find_credential_for_host(
    host: str,
    path: str,
    toolkit_id: str,
    alias: str | None,
    service: str | None = None,
) -> tuple[dict[str, str], str | None, str | None, bool]:
    """
    Return (headers_to_inject, api_id, credential_id, is_ambiguous) for the given upstream host.

    credential_id is the ID of the first credential used for injection — used by the
    caller to enforce per-credential policy rules.

    is_ambiguous is True when multiple credentials matched and no alias/service
    was provided to disambiguate.
    """
    import logging as _log
    _broker_log = _log.getLogger("jentic.broker")

    # Resolve host → api_id
    candidates = [host]
    parts = host.split(".")
    if len(parts) > 2:
        candidates.append(".".join(parts[1:]))

    api_id = None
    async with get_db() as db:
        for candidate in candidates:
            # For subdomain-style hosts (e.g. calendar.googleapis.com), also try
            # the catalog convention of parent-domain/subdomain (googleapis.com/calendar)
            # by extracting the leftmost subdomain label as a path hint.
            sub_hint = host.split(".")[0] if host != candidate else None
            row = None

            # 1. Exact match
            async with db.execute("SELECT id FROM apis WHERE id=?", (candidate,)) as cur:
                row = await cur.fetchone()

            # 2. Subdomain-hinted prefix match (e.g. googleapis.com/calendar)
            if not row and sub_hint:
                async with db.execute(
                    "SELECT id FROM apis WHERE id LIKE ? ORDER BY length(id) DESC LIMIT 1",
                    (f"{candidate}/{sub_hint}%",),
                ) as cur:
                    row = await cur.fetchone()

            # 3. General longest-prefix match (fallback)
            if not row:
                async with db.execute(
                    "SELECT id FROM apis WHERE id LIKE ? ORDER BY length(id) DESC LIMIT 1",
                    (f"{candidate}%",),
                ) as cur:
                    row = await cur.fetchone()

            if row:
                api_id = row[0]
                break

    # Credentials are always stored under api_id (the canonical ID from the apis
    # table), which matches how POST /credentials stores them and how
    # _resolve_credential_ids (the policy check path) looks them up.
    _broker_log.debug("CRED LOOKUP: host=%r → api_id=%r (toolkit=%r alias=%r)", host, api_id, toolkit_id, alias)

    if not api_id:
        return {}, None, None, False

    # Get credentials bound to this toolkit + api
    creds = await vault.get_credentials_for_api(toolkit_id, api_id)
    # TODO: remove hostname fallback once Pipedream credential storage is
    # updated to use catalog api_id instead of HTTP hostname (see #79).
    if not creds and host != api_id:
        creds = await vault.get_credentials_for_api(toolkit_id, host)
    _broker_log.debug("CRED LOOKUP: %d cred(s) for api_id=%r host=%r: %s", len(creds), api_id, host, [c.get("id") for c in creds])

    if not creds and toolkit_id:
        # Don't block no-auth APIs — only raise if the API spec defines security schemes.
        # If someone added an overlay with security schemes, they'd also have created
        # a credential — so creds wouldn't be empty and we'd never reach this branch.
        if await api_has_native_scheme(api_id):
            raise ValueError(
                f"No credentials found for host '{host}' (resolved api_id '{api_id}') "
                f"in toolkit '{toolkit_id}'. "
                f"Use POST /toolkits/{toolkit_id}/access-requests to request access."
            )

    is_ambiguous = False

    if alias and creds:
        matched = [c for c in creds if c.get("id") == alias]
        if matched:
            _broker_log.debug("CRED LOOKUP: alias %r matched → using %r", alias, matched[0].get("id"))
            creds = matched
        else:
            _broker_log.warning("CRED LOOKUP: alias %r not found in %s — falling back to first cred", alias, [c.get("id") for c in creds])
        # If alias doesn't match any credential, fall through with all creds (best-effort)

    elif service and creds and len(creds) > 1:
        # X-Jentic-Service: select by Pipedream app_slug (e.g. "google_calendar")
        # Look up which credentials belong to accounts with this app_slug.
        async with get_db() as db:
            async with db.execute(
                "SELECT id FROM credentials WHERE id IN "
                "(SELECT broker_id || '-' || account_id || '-' || replace(api_host, '.', '-') "
                " FROM oauth_broker_accounts WHERE app_slug=?)",
                (service,),
            ) as cur:
                service_cred_ids = {r[0] for r in await cur.fetchall()}
        matched = [c for c in creds if c["id"] in service_cred_ids]
        if matched:
            _broker_log.debug("CRED LOOKUP: service %r matched %d cred(s)", service, len(matched))
            creds = matched
        else:
            # Service name doesn't match any credential for this host — fail with
            # a 409 listing available services so the agent can self-correct.
            async with get_db() as db:
                async with db.execute(
                    "SELECT DISTINCT app_slug FROM oauth_broker_accounts "
                    "WHERE api_host=? AND app_slug IS NOT NULL",
                    (host,),
                ) as cur:
                    available = [r[0] for r in await cur.fetchall()]
            raise ServiceNotFoundError(
                f"Service '{service}' not found for host '{host}'. "
                f"Available services: {available}"
            )

    if len(creds) > 1 and not alias and not service:
        is_ambiguous = True
        _broker_log.warning(
            "CRED AMBIGUITY: %d credentials for host=%r api_id=%r — using first. "
            "Set X-Jentic-Service or X-Jentic-Credential header to disambiguate. "
            "Credential IDs: %s",
            len(creds), host, api_id,
            [c.get("id") for c in creds],
        )

    # Get merged security schemes (spec + confirmed overlays)
    from src.routers.overlays import get_merged_security_schemes
    schemes = await get_merged_security_schemes(api_id)

    # Note: schemes may be empty if no spec or overlay is registered for this API.
    # That is fine — credentials with an explicit auth_type can still be injected
    # without a scheme definition (e.g. github.com git-over-HTTPS has no spec).

    headers = {}
    first_credential_id: str | None = None
    for cred in creds:
        value = cred["value"]
        auth_type = cred.get("auth_type")
        identity = cred.get("identity")

        # Derive auth_type from spec if not stored on credential (legacy / null)
        if not auth_type:
            _basic_key = next(
                (k for k, v in schemes.items() if v.get("type") == "http" and v.get("scheme", "").lower() == "basic"),
                None,
            )
            _bearer_key = next(
                (k for k, v in schemes.items() if v.get("type") == "http" and v.get("scheme", "").lower() == "bearer"),
                None,
            )
            _apikey_key = next(
                (k for k, v in schemes.items() if v.get("type") == "apiKey"),
                None,
            )
            if _basic_key:
                auth_type = "basic"
            elif _bearer_key:
                auth_type = "bearer"
            elif _apikey_key:
                auth_type = "apiKey"

        if not auth_type:
            continue

        if not first_credential_id:
            first_credential_id = cred["id"]

        # Find the matching scheme(s) in the spec by auth_type
        if auth_type == "bearer":
            # Find any HTTP auth scheme that isn't basic/digest.
            # Use the actual scheme name from the spec/overlay — e.g. "bearer" → "Bearer",
            # "token" → "Token". This lets vendor-specific prefixes (Deepgram "Token",
            # GitHub "Bearer", etc.) work without touching the credential.
            scheme = next(
                (v for v in schemes.values()
                 if v.get("type") == "http" and v.get("scheme", "").lower() not in ("basic", "digest")),
                None,
            )
            if scheme:
                scheme_prefix = scheme.get("scheme", "bearer").capitalize()
                headers["Authorization"] = f"{scheme_prefix} {value}"
            else:
                # No overlay/spec scheme found — fall back to Bearer (most common)
                headers["Authorization"] = f"Bearer {value}"

        elif auth_type == "basic":
            scheme = next(
                (v for v in schemes.values() if v.get("type") == "http" and v.get("scheme", "").lower() in ("basic", "digest")),
                None,
            )
            # Inject Basic auth regardless of whether a scheme is found in the spec.
            # auth_type on the credential is authoritative — no spec/overlay required.
            # (scheme lookup is kept for future use, e.g. digest challenge-response)
            import base64 as _b64
            # BasicAuth/DigestAuth credential construction (RFC 7617):
            # 1. value contains ":" → treat as pre-formatted "username:password"
            # 2. identity is set → base64("{identity}:{value}")
            # 3. fallback → base64("token:{value}") — works for PAT-style APIs like GitHub
            if ":" in value:
                _raw = value
            elif identity:
                _raw = f"{identity}:{value}"
            else:
                _raw = f"token:{value}"
            headers["Authorization"] = f"Basic {_b64.b64encode(_raw.encode()).decode()}"

        elif auth_type == "apiKey":
            # Collect all apiKey schemes from the spec
            apikey_schemes = {k: v for k, v in schemes.items() if v.get("type") == "apiKey"}
            if not apikey_schemes:
                continue

            # Canonical compound apiKey: overlay uses scheme names 'Secret' and 'Identity'
            secret_scheme = apikey_schemes.get("Secret")
            identity_scheme = apikey_schemes.get("Identity")
            if secret_scheme and identity_scheme:
                # Compound: Secret → cred.value, Identity → cred.identity
                if secret_scheme.get("in") == "header":
                    headers[secret_scheme["name"]] = value
                if identity_scheme.get("in") == "header" and identity:
                    headers[identity_scheme["name"]] = identity
            else:
                # Single apiKey: inject value into every apiKey header scheme
                for scheme in apikey_schemes.values():
                    if scheme.get("in") == "header":
                        headers[scheme["name"]] = value

        elif auth_type == "oauth2":
            headers["Authorization"] = f"Bearer {value}"

    _broker_log.debug("CRED INJECT: api_id=%r injecting headers=%s using cred=%r ambiguous=%s", api_id, list(headers.keys()), first_credential_id, is_ambiguous)
    return headers, api_id, first_credential_id, is_ambiguous


async def _find_pipedream_credential_for_host(
    host: str,
    path: str,
    toolkit_id: str | None,
    alias: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (account_id, credential_id) for a Pipedream-managed credential in this toolkit.

    Pipedream credentials have auth_type='pipedream_oauth' and their encrypted value
    IS the Pipedream account_id (apn_xxx). This bypasses the apis table lookup —
    Pipedream-connected APIs may not have a spec in the local catalog.

    Uses longest-prefix matching: the credential whose api_id is the longest prefix
    of (host + path) wins. This correctly disambiguates googleapis.com/calendar from
    googleapis.com/gmail when both are provisioned.

    If alias is specified, only the credential with that ID is considered.
    Returns (None, None) if no Pipedream credential is provisioned for this host+toolkit.
    """
    if not toolkit_id:
        return None, None
    full_path = host + path  # e.g. "googleapis.com/calendar/v3/calendars/primary"
    from src.db import DEFAULT_TOOLKIT_ID
    async with get_db() as db:
        if alias:
            # Caller specified an exact credential — use it directly if it's Pipedream
            async with db.execute(
                "SELECT id, encrypted_value FROM credentials "
                "WHERE id=? AND auth_type='pipedream_oauth'",
                (alias,),
            ) as cur:
                row = await cur.fetchone()
        elif toolkit_id == DEFAULT_TOOLKIT_ID:
            # Longest-prefix match: find the credential whose api_id is a prefix of host+path
            async with db.execute(
                "SELECT id, encrypted_value FROM credentials "
                "WHERE ? LIKE (api_id || '%') AND auth_type='pipedream_oauth' "
                "ORDER BY length(api_id) DESC LIMIT 1",
                (full_path,),
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute(
                """SELECT c.id, c.encrypted_value FROM credentials c
                   JOIN toolkit_credentials tc ON tc.credential_id = c.id
                   WHERE tc.toolkit_id=? AND ? LIKE (c.api_id || '%')
                   AND c.auth_type='pipedream_oauth'
                   ORDER BY length(c.api_id) DESC LIMIT 1""",
                (toolkit_id, full_path),
            ) as cur:
                row = await cur.fetchone()
    if not row:
        return None, None
    return vault.decrypt(row[1]), row[0]



def _is_broker_path(path: str) -> bool:
    """True if the path looks like an upstream host prefix (contains a dot)."""
    if not path or path == "/":
        return False
    first_segment = path.lstrip("/").split("/")[0]
    return "." in first_segment and not first_segment.startswith(".")


# Custom Starlette path convertor so the broker catch-all only matches paths
# whose first segment looks like a hostname (contains a dot, e.g. api.stripe.com).
# This means UI routes like /search or /catalog never reach the broker at all —
# they are handled by earlier registered routes or the SPA catch-all in main.py.
from starlette.convertors import Convertor, CONVERTOR_TYPES  # noqa: E402

class _BrokerHostConvertor(Convertor):
    # First segment must contain a dot, not start with one, and have at least one char before the dot.
    # Rejects: .well-known/..., /@vite/..., empty first segment
    # Matches: api.stripe.com/v1/customers, httpbin.org/get
    regex = r"[^/.][^/]*\.[^/.][^/]*(?:/.*)?$"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        return value

CONVERTOR_TYPES["brokerhost"] = _BrokerHostConvertor()


_BROKER_DESCRIPTION = (
    "Routes any HTTP request to the upstream API, injecting credentials automatically.\n\n"
    "URL shape: `/{upstream_host}/{path}` — e.g. `/api.stripe.com/v1/customers`\n\n"
    "All HTTP methods supported; Swagger UI shows GET as representative.\n\n"
    "**Headers:**\n"
    "- `X-Jentic-Simulate: true` — validate and preview the call without sending it\n"
    "- `X-Jentic-Credential: {alias}` — select a specific credential when multiple exist for an API\n"
    "- `X-Jentic-Service: {app_slug}` — select by service name (e.g. `google_calendar`, `gmail`) when multiple credentials share a host\n"
    "- `X-Jentic-Dry-Run: true` — alias for Simulate (deprecated)\n\n"
    "Returns upstream response verbatim plus `X-Jentic-Execution-Id` for trace correlation."
)

_BROKER_RESPONSES = {
    200: {
        "description": "Upstream response proxied verbatim. Content-Type matches upstream.",
        "content": {
            "application/json": {"schema": {}},
            "text/html": {},
            "text/plain": {},
        },
    },
    202: {"description": "Async job created (RFC 7240). Poll via Location header or GET /jobs/{job_id}"},
    400: {"description": "Bad request (upstream or Jentic validation)"},
    401: {"description": "Missing or rejected credential"},
    403: {"description": "Policy denied or upstream forbidden"},
    404: {"description": "Upstream resource not found"},
    502: {"description": "Upstream unreachable"},
}


# ── Documentation stub ────────────────────────────────────────────────────────
# Swagger UI breaks when multiple HTTP methods share the same catch-all path
# (it collapses them and uses the wrong verb in "Try it out"). We hide the real
# multi-method handler from the schema and expose a single GET stub for docs.
# The real handler below is include_in_schema=False.

@router.get(
    "/{target:brokerhost}",
    include_in_schema=True,
    tags=["execute"],
    summary="Broker — proxy a call to any registered API with automatic credential injection",
    description=_BROKER_DESCRIPTION,
    responses=_BROKER_RESPONSES,
    operation_id="broker_get",
    openapi_extra=agent_hints(
        when_to_use="Use this after you've inspected an operation via GET /inspect/{id} and are ready to execute it. The broker automatically injects credentials from the toolkit's vault, enforces access policies, and traces all calls. URL format: /{upstream_host}/{path} (e.g., /api.stripe.com/v1/payment_intents). Supports all HTTP methods (GET, POST, PUT, PATCH, DELETE).",
        prerequisites=[
            "Requires authentication (toolkit key or human session)",
            "Requires registered API with credentials (use POST /credentials to add)",
            "Requires credential bound to toolkit (use PUT /toolkits/{id}/credentials/{cred_id})",
            "Toolkit credential must allow the operation (governed by access policy)"
        ],
        avoid_when="Do not use for workflows — use POST /workflows/{slug} instead. Do not use for Jentic internal endpoints — use direct paths like /apis, /search.",
        related_operations=[
            "GET /inspect/{id} — inspect operation before calling to see parameters and auth requirements",
            "GET /traces/{id} — view execution trace after broker call (use X-Jentic-Execution-Id header)",
            "GET /jobs/{id} — poll async job status when Prefer: wait=0 header is used",
            "POST /credentials — add credentials before calling",
            "PUT /toolkits/{id}/credentials/{cred_id} — bind credentials to toolkit"
        ]
    ),
)
async def broker_doc_stub(
    request: Request,
    target: Annotated[str, Path(description="Upstream API path (format: host.domain/path, e.g. api.github.com/repos)")]
):
    """Documentation stub — delegates to the real broker handler."""
    return await broker(request, target)


@router.api_route(
    "/{target:brokerhost}",
    methods=["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def broker(request: Request, target: str):
    """
    Catch-all broker route. Fires only for paths that look like upstream hosts
    (first segment contains a dot). All Jentic-internal routes are registered first
    and take priority.
    """
    if not _is_broker_path("/" + target):
        raise HTTPException(404, "Not found")

    # URL-decode the target — Swagger UI encodes slashes as %2F, so
    # /%2Ftechpreneurs.ie%2Flatest.json arrives as %2Ftechpreneurs.ie%2Flatest.json.
    # Decode and strip any leading slash so both forms work identically.
    target = unquote(target).lstrip("/")

    # Parse upstream host and path from target
    parts = target.split("/", 1)
    upstream_host = parts[0]
    upstream_path = "/" + parts[1] if len(parts) > 1 else "/"

    # ── Workflow dispatch ─────────────────────────────────────────────────────
    # If the target host is the Jentic host itself and path is /workflows/{slug},
    # route to the arazzo orchestrator internally instead of making an HTTP call.
    # Also detect self-referential calls via the request's Host header
    # (handles cases where the container doesn't have env vars set)
    _request_host = request.headers.get("host", "").split(":")[0]
    _is_self = (
        upstream_host == JENTIC_PUBLIC_HOSTNAME
        or upstream_host == _request_host
        or upstream_host in ("localhost", "127.0.0.1", "0.0.0.0")
    )
    if _is_self and upstream_path.startswith("/workflows/"):
        slug = upstream_path.split("/workflows/", 1)[1].split("/")[0]
        if slug:
            from src.routers.workflows import dispatch_workflow
            from src.utils import parse_prefer_wait
            body_bytes_wf = await request.body()
            caller_key = (
                request.headers.get("x-jentic-api-key")
                or ""
            )
            toolkit_id_wf = getattr(request.state, "toolkit_id", None)
            simulate_wf = (
                getattr(request.state, "simulate", False)
                or request.headers.get("x-jentic-simulate", "").lower() == "true"
            )
            prefer_wait_wf = parse_prefer_wait(request.headers.get("prefer"))
            callback_url_wf = request.headers.get("x-jentic-callback")
            return await dispatch_workflow(
                slug=slug,
                body_bytes=body_bytes_wf,
                caller_api_key=caller_key,
                toolkit_id=toolkit_id_wf,
                simulate=simulate_wf,
                prefer_wait=prefer_wait_wf,
                callback_url=callback_url_wf,
            )

    execution_id = new_trace_id()
    started_at = time.time()

    # Helper to write broker traces (reduces duplication across 10+ call sites)
    async def _write_trace(status: str, http_status: int, error: str | None = None) -> None:
        """Write trace for this broker call. All broker exit points should call this."""
        if not is_simulate:
            await safe_write_trace(
                trace_id=execution_id,
                toolkit_id=toolkit_id,
                operation_id=f"{request.method}/{upstream_host}{upstream_path}",
                workflow_id=None,
                spec_path=None,
                status=status,
                http_status=http_status,
                duration_ms=int((time.time() - started_at) * 1000),
                error=error,
                step_outputs=None,
            )
    # toolkit_id is None for unauthenticated (anonymous) requests —
    # credential injection and policy checks are skipped in that case.
    toolkit_id: str | None = getattr(request.state, "toolkit_id", None)
    is_simulate = (
        getattr(request.state, "simulate", False)
        or request.headers.get("x-jentic-simulate", "").lower() == "true"
    )
    credential_alias = request.headers.get("x-jentic-credential")
    credential_service = request.headers.get("x-jentic-service")
    callback_url = request.headers.get("x-jentic-callback")
    if callback_url and not is_http_https_url(callback_url):
        raise HTTPException(400, "X-Jentic-Callback must be an http or https URL")

    # ── Killswitch: reject all requests for disabled toolkits ─────────────────
    if toolkit_id:
        async with get_db() as _ks_db:
            async with _ks_db.execute(
                "SELECT disabled FROM toolkits WHERE id=?", (toolkit_id,)
            ) as _ks_cur:
                _ks_row = await _ks_cur.fetchone()
        if _ks_row and _ks_row[0]:
            return Response(
                content=json.dumps({
                    "error": "toolkit_suspended",
                    "message": f"Toolkit '{toolkit_id}' has been suspended. All API access is blocked. Contact the toolkit owner to restore access.",
                    "toolkit_id": toolkit_id,
                }),
                status_code=403,
                media_type="application/json",
                headers={"X-Jentic-Error": "true"},
            )

    # ── Prefer: wait=N for single broker calls ────────────────────────────────
    # Parsed here and threaded through to the async path below if the upstream
    # call takes too long.
    from src.utils import parse_prefer_wait
    prefer_wait = parse_prefer_wait(request.headers.get("prefer"))

    # ── Resolve credential IDs (no decryption) → policy check ────────────────
    # We resolve the api_id and credential IDs first — without decrypting —
    # so policy can be enforced before the vault is ever touched.
    # Denied requests never decrypt a credential.
    #
    # X-Jentic-Credential is a HARD OVERRIDE: when the caller names a specific
    # credential, policy is checked against THAT credential — not whatever the
    # host-matching heuristic would pick. This is critical for multi-service hosts
    # (e.g. googleapis.com) where auto-selection would otherwise target the wrong
    # credential (e.g. Calendar when the caller wants Gmail), causing spurious 403s
    # with a misleading credential_id in the error body.
    _api_id_for_host: str | None = None
    _resolved_cred_ids: list[str] = []

    if credential_alias and toolkit_id:
        # Hard override: use the named credential directly for policy enforcement.
        # Also attempt to resolve api_id for context (error messages etc.) but
        # never let it change which credential gets checked.
        _resolved_cred_ids = [credential_alias]
        try:
            _api_id_for_host, _ = await _resolve_credential_ids(
                host=upstream_host, toolkit_id=toolkit_id
            )
        except Exception:
            pass
    elif toolkit_id:
        try:
            _api_id_for_host, _resolved_cred_ids = await _resolve_credential_ids(
                host=upstream_host, toolkit_id=toolkit_id
            )
        except Exception:
            # Fail closed: if we can't resolve credentials for policy checking,
            # don't proceed to credential injection — deny the request.
            # Only applies to authenticated requests; anonymous passthrough
            # skips credential resolution entirely.
            log.exception("Credential resolution failed for %r (toolkit=%s)",
                          upstream_host, toolkit_id)
            await _write_trace("error", 500, f"Credential resolution failed for {upstream_host}")
            return Response(
                content=json.dumps({
                    "error": "CREDENTIAL_RESOLUTION_FAILED",
                    "message": f"Could not resolve credentials for '{upstream_host}'. Request denied (fail-closed).",
                }),
                status_code=500,
                media_type="application/json",
                headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
            )

    if toolkit_id and _resolved_cred_ids:
        from src.routers.toolkits import check_credential_policy
        # Check against the first matched credential (primary).
        # When credential_alias is set this is always the aliased credential.
        primary_cred_id = _resolved_cred_ids[0]
        try:
            allowed, reason = await check_credential_policy(
                credential_id=primary_cred_id,
                operation_id=f"{request.method}/{upstream_host}{upstream_path}",
                method=request.method,
                path=upstream_path,
            )
            if not allowed:
                await _write_trace("policy_denied", 403, f"Policy denied: {reason}")
                error_body = {
                    "error": "policy_denied",
                    "message": f"{request.method} {upstream_host}{upstream_path} denied by credential policy. {reason}",
                    "credential_id": primary_cred_id,
                    "toolkit_id": toolkit_id,
                    "remediation": f"POST /toolkits/{toolkit_id}/access-requests to request expanded permissions.",
                }
                return Response(
                    content=json.dumps(error_body),
                    status_code=403,
                    media_type="application/json",
                    headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
                )
        except Exception:
            # Fail closed: if the policy check itself errors, deny the request
            # rather than allowing it through unchecked.
            log.exception("Policy check failed for %s %r %r (cred=%s)",
                          request.method, upstream_host, upstream_path, primary_cred_id)
            await _write_trace("error", 403, f"Policy check failed for {request.method} {upstream_host}{upstream_path} (credential {primary_cred_id})")
            return Response(
                content=json.dumps({
                    "error": "POLICY_CHECK_FAILED",
                    "message": f"Policy evaluation failed for credential '{primary_cred_id}'. Request denied (fail-closed).",
                    "credential_id": primary_cred_id,
                    "toolkit_id": toolkit_id,
                }),
                status_code=403,
                media_type="application/json",
                headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
            )

    # body_bytes initialised here so the OAuthBroker fallback can read it
    # without a double-read; the main forward path reads it again below if empty.
    body_bytes: bytes = b""

    # ── Full credential lookup (with decryption) ──────────────────────────────
    try:
        inject_headers, api_id, credential_id, credential_ambiguous = await _find_credential_for_host(
            host=upstream_host,
            path=upstream_path,
            toolkit_id=toolkit_id,
            alias=credential_alias,
            service=credential_service,
        )
    except ServiceNotFoundError as e:
        await _write_trace("error", 409, str(e))
        return Response(
            content=json.dumps({"error": "SERVICE_NOT_FOUND", "message": str(e)}),
            status_code=409,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
        )
    except Exception as e:
        log.exception("Credential lookup failed")
        await _write_trace("error", 500, "Credential lookup failed")
        error_body = {"error": "CREDENTIAL_LOOKUP_FAILED", "message": "Internal error during credential lookup."}
        return Response(
            content=json.dumps(error_body),
            status_code=500,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
        )

    # Credential-related headers — included on all responses (success and error)
    _cred_headers: dict[str, str] = {}
    if credential_id:
        _cred_headers["X-Jentic-Credential-Used"] = credential_id
    if credential_ambiguous:
        _cred_headers["X-Jentic-Credential-Ambiguous"] = "true"

    # ── Compute routing host (used by both main and Pipedream paths) ──────────
    # Look up base_url from the apis table for the matched api_id. This decouples
    # the api_id (e.g. googleapis.com/calendar) from the real HTTP host
    # (www.googleapis.com). Falls back to upstream_host if no base_url found.
    routing_host = upstream_host
    if api_id and not _is_self:
        async with get_db() as _rdb:
            async with _rdb.execute("SELECT base_url FROM apis WHERE id=?", (api_id,)) as _rcur:
                _rrow = await _rcur.fetchone()
            if _rrow and _rrow[0]:
                _parsed_host = urlparse(_rrow[0]).hostname
                if _parsed_host:
                    routing_host = _parsed_host

    # ── Pipedream credential path ─────────────────────────────────────────────
    # If the vault lookup yielded no headers, check for an explicitly-provisioned
    # Pipedream credential (auth_type='pipedream_oauth'). This path requires:
    #   1. POST /oauth-brokers/{id}/sync  — creates the credential in the vault
    #   2. POST /toolkits/{id}/credentials — explicitly provisions it to this toolkit
    # No implicit fallback. If no credential is provisioned, we fall through to
    # unauthenticated forwarding (or the request will fail upstream with 401).
    if not inject_headers:
        pd_account_id, pd_cred_id = await _find_pipedream_credential_for_host(
            upstream_host, upstream_path, toolkit_id, alias=credential_alias
        )
        if pd_account_id and pd_cred_id:
            # Policy check for this Pipedream credential (same gate as vault path)
            if toolkit_id:
                try:
                    from src.routers.toolkits import check_credential_policy
                    allowed, reason = await check_credential_policy(
                        credential_id=pd_cred_id,
                        operation_id=f"{request.method}/{upstream_host}{upstream_path}",
                        method=request.method,
                        path=upstream_path,
                    )
                    if not allowed:
                        await _write_trace("policy_denied", 403, f"Policy denied: {reason}")
                        error_body = {
                            "error": "policy_denied",
                            "message": f"{request.method} {upstream_host}{upstream_path} denied. {reason}",
                            "credential_id": pd_cred_id,
                            "toolkit_id": toolkit_id,
                            "remediation": f"POST /toolkits/{toolkit_id}/access-requests",
                        }
                        return Response(
                            content=json.dumps(error_body),
                            status_code=403,
                            media_type="application/json",
                            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
                        )
                except Exception:
                    log.exception("Pipedream policy check failed for %s %r %r (cred=%s)",
                                  request.method, upstream_host, upstream_path, pd_cred_id)
                    await _write_trace("error", 403, f"Policy check failed for {request.method} {upstream_host}{upstream_path} (credential {pd_cred_id})")
                    return Response(
                        content=json.dumps({
                            "error": "POLICY_CHECK_FAILED",
                            "message": f"Policy evaluation failed for credential '{pd_cred_id}'. Request denied (fail-closed).",
                            "credential_id": pd_cred_id,
                            "toolkit_id": toolkit_id,
                        }),
                        status_code=403,
                        media_type="application/json",
                        headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
                    )

            # Find the Pipedream broker instance and proxy using the credential's account_id
            from src.oauth_broker import registry as _oauth_registry
            # Always use the external_user_id stored against this account in the DB —
            # never trust the caller-supplied header, which may differ (e.g. sdk sends
            # michael@jentic.com but the account was registered under "default")
            _ext_user = "default"
            async with get_db() as _eudb:
                async with _eudb.execute(
                    "SELECT external_user_id FROM oauth_broker_accounts WHERE account_id=? LIMIT 1",
                    (pd_account_id,),
                ) as _eucur:
                    _eurow = await _eucur.fetchone()
                    if _eurow:
                        _ext_user = _eurow[0]
            _pd_broker = None
            for _b in _oauth_registry.brokers:
                if hasattr(_b, "proxy_request_with_account"):
                    _pd_broker = _b
                    break

            if _pd_broker is not None:
                if not body_bytes:
                    body_bytes = await request.body()
                _fwd_hdrs = {
                    k: v for k, v in request.headers.items()
                    if k.lower() not in _HOP_BY_HOP
                }
                _pd_resp = await _pd_broker.proxy_request_with_account(
                    account_id=pd_account_id,
                    api_host=routing_host,
                    upstream_path=upstream_path,
                    method=request.method,
                    headers=_fwd_hdrs,
                    body=body_bytes,
                    query_string=request.url.query,
                    external_user_id=_ext_user,
                )
                if _pd_resp is not None:
                    # Write trace for Pipedream proxy call
                    trace_status = "success" if _pd_resp.status_code < 400 else "error"
                    await _write_trace(trace_status, _pd_resp.status_code)
                    _pd_resp_headers = {
                        k: v for k, v in _pd_resp.headers.items()
                        if k.lower() not in _HOP_BY_HOP
                    }
                    _pd_resp_headers["X-Jentic-Execution-Id"] = execution_id
                    _pd_resp_headers["X-Jentic-OAuth-Broker"] = "pipedream"
                    _pd_resp_headers["X-Jentic-Credential-Id"] = pd_cred_id
                    return Response(
                        content=_pd_resp.content,
                        status_code=_pd_resp.status_code,
                        headers=_pd_resp_headers,
                        media_type=_pd_resp.headers.get("content-type"),
                    )

    # ── Build upstream URL ────────────────────────────────────────────────────
    # routing_host was computed above from base_url lookup — use it here too.
    import os as _os2
    _internal_port = int(_os2.environ.get("JENTIC_INTERNAL_PORT", "8900"))
    if _is_self:
        upstream_url = f"http://localhost:{_internal_port}{upstream_path}"
    else:
        upstream_url = f"https://{routing_host}{upstream_path}"
    if request.url.query:
        upstream_url += f"?{request.url.query}"

    # ── Simulate: return what would be sent ──────────────────────────────────
    if is_simulate:
        body_bytes = await request.body()
        forward_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP
        }
        forward_headers.update(inject_headers)
        would_send = {
            "method": request.method,
            "url": upstream_url,
            "headers": {
                k: ("***" if k.lower() == "authorization" else v)
                for k, v in forward_headers.items()
            },
        }
        if body_bytes:
            try:
                would_send["body"] = json.loads(body_bytes)
            except Exception:
                would_send["body"] = body_bytes.decode("utf-8", errors="replace")

        return Response(
            content=json.dumps({
                "simulate": True,
                "synthesised": False,
                "valid": True,
                "would_send": would_send,
            }),
            status_code=200,
            media_type="application/json",
            headers={"X-Jentic-Execution-Id": execution_id},
        )

    # ── Build forwarded headers ───────────────────────────────────────────────
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    # Strip inbound auth headers before injecting vault credentials —
    # prevents duplicate Authorization when toolkit key arrives as Basic auth
    # (e.g. git embedding the key in the remote URL).
    if inject_headers:
        forward_headers.pop("authorization", None)
    # Inject credentials (replaces any auth header)
    forward_headers.update(inject_headers)

    # ── Forward request ───────────────────────────────────────────────────────
    body_bytes = await request.body()

    # ── Prefer: wait=0 → async broker call ───────────────────────────────────
    if prefer_wait is not None and prefer_wait == 0.0:
        from src.routers.jobs import create_job, update_job, _running_tasks
        capability_id = f"{request.method}/{upstream_host}{upstream_path}"
        job_id = await create_job(
            kind="broker",
            slug_or_id=capability_id,
            toolkit_id=toolkit_id,
            inputs={},
        )
        if callback_url:
            async with get_db() as _db:
                await _db.execute(
                    "UPDATE jobs SET callback_url=? WHERE id=?", (callback_url, job_id)
                )
                await _db.commit()

        async def _broker_bg():
            try:
                await update_job(job_id, status="running")
                fwd_hdrs = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
                fwd_hdrs.update(inject_headers)
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as cl:
                    resp = await cl.request(request.method, upstream_url, headers=fwd_hdrs, content=body_bytes or None)
                upstream_async_flag = resp.status_code == 202
                upstream_loc = resp.headers.get("location") if upstream_async_flag else None
                result = {"status_code": resp.status_code, "body": resp.text[:4096]}

                # Update trace with final status
                trace_status = "success" if resp.status_code < 400 else "error"
                await _write_trace(trace_status, resp.status_code)

                if upstream_async_flag:
                    await update_job(job_id, status="upstream_async", result=result,
                                     http_status=202, upstream_async=True, upstream_job_url=upstream_loc)
                elif resp.status_code < 400:
                    await update_job(job_id, status="complete", result=result, http_status=resp.status_code)
                else:
                    await update_job(job_id, status="failed", error=resp.text[:512], http_status=resp.status_code)
            except Exception as exc:
                # Update trace on exception
                await _write_trace("error", 500, f"Background task error: {str(exc)}")
                await update_job(job_id, status="failed", error=str(exc))
            finally:
                _running_tasks.pop(job_id, None)

        task = asyncio.create_task(_broker_bg())
        _running_tasks[job_id] = task

        # Write pending trace (will be updated by background task)
        await _write_trace("pending", 202)

        return Response(
            content=json.dumps({
                "status": "running",
                "job_id": job_id,
                "_links": {"poll": f"/jobs/{job_id}"},
                "message": "Request dispatched asynchronously. Poll _links.poll for completion.",
            }),
            status_code=202,
            media_type="application/json",
            headers={"Location": f"/jobs/{job_id}", "X-Jentic-Job-Id": job_id, "X-Jentic-Execution-Id": execution_id},
        )

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=forward_headers,
                content=body_bytes if body_bytes else None,
            )
    except httpx.TimeoutException:
        await _write_trace("timeout", 504, f"Upstream {upstream_host} timeout after 60s")
        error_body = {
            "error": "UPSTREAM_TIMEOUT",
            "message": f"Upstream {upstream_host} did not respond within 60s",
        }
        return Response(
            content=json.dumps(error_body),
            status_code=504,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id, **_cred_headers},
        )
    except httpx.RequestError as e:
        log.exception("Upstream request failed for %s", upstream_host)
        await _write_trace("error", 502, f"Network error reaching {upstream_host}")
        error_body = {
            "error": "UPSTREAM_UNREACHABLE",
            "message": f"Could not reach {upstream_host}.",
        }
        return Response(
            content=json.dumps(error_body),
            status_code=502,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id, **_cred_headers},
        )

    # ── Build response — strip hop-by-hop, add Jentic trace headers ──────────
    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    response_headers["X-Jentic-Execution-Id"] = execution_id
    response_headers.update(_cred_headers)

    # ── Confirm pending overlay on first successful call ──────────────────────
    if api_id and upstream_response.status_code < 400:
        try:
            from src.routers.overlays import confirm_overlay
            await confirm_overlay(api_id, execution_id)
        except Exception:
            pass  # non-fatal

    # ── Auth failure hint for BasicAuth ───────────────────────────────────────
    # When a BasicAuth call gets 401/403, the likely cause is the wrong
    # username format. Surface a machine-readable hint so agents can
    # self-correct by researching and uploading an overlay.
    if upstream_response.status_code in (401, 403):
        auth_header = inject_headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            hint = {
                "x-jentic-hint": "basic_auth_failure",
                "message": (
                    f"BasicAuth to {upstream_host} failed ({upstream_response.status_code}). "
                    "The credential value may be correct but the identity (username) is wrong. "
                    "PATCH /credentials/{id} with the correct 'identity' field. "
                    "For most token-based APIs any username works; for traditional user/password APIs "
                    "the identity must match the actual account username."
                ),
                "action": f"PATCH /credentials/{{id}}",
                "example": {"identity": "your_username_here"},
                "upstream_status": upstream_response.status_code,
                "upstream_body": upstream_response.text[:512],
            }
            response_headers["X-Jentic-Hint"] = "basic_auth_failure"
            # Write trace for BasicAuth failure hint path
            await _write_trace("error", upstream_response.status_code, "BasicAuth failure - identity mismatch")
            return Response(
                content=json.dumps(hint),
                status_code=upstream_response.status_code,
                headers=response_headers,
                media_type="application/json",
            )

    # ── Detect upstream 202: surface as upstream_async ───────────────────────
    # If the upstream itself returned 202, and a callback was registered,
    # create a job record so the agent has a consistent handle.
    if upstream_response.status_code == 202 and callback_url:
        from src.routers.jobs import create_job, update_job
        upstream_loc = upstream_response.headers.get("location")
        capability_id = f"{request.method}/{upstream_host}{upstream_path}"
        job_id = await create_job(
            kind="broker", slug_or_id=capability_id,
            toolkit_id=toolkit_id, inputs={},
        )
        async with get_db() as _db:
            await _db.execute("UPDATE jobs SET callback_url=? WHERE id=?", (callback_url, job_id))
            await _db.commit()
        await update_job(
            job_id, status="upstream_async",
            result={"body": upstream_response.text[:4096]},
            http_status=202, upstream_async=True, upstream_job_url=upstream_loc,
        )
        response_headers["X-Jentic-Job-Id"] = job_id
        response_headers["Location"] = f"/jobs/{job_id}"

    # Write trace for standard path (includes 202 upstream async case)
    trace_status = "success" if upstream_response.status_code < 400 else "error"
    await _write_trace(trace_status, upstream_response.status_code)

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
