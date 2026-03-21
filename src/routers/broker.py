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
  X-Jentic-Credential — credential alias when multiple creds exist for same API
  X-Jentic-Callback   — webhook URL for async result delivery (TODO: phase 2)

Response headers added:
  X-Jentic-Error      — "true" when the error is from Jentic, not upstream
  X-Jentic-Execution-Id — UUID for this broker call (for tracing)
"""
import json
import time
import uuid
import asyncio
from typing import Optional
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.routing import APIRoute

from src.db import get_db
import src.vault as vault
# Lazy import to avoid circular deps — imported inline where needed
# from src.routers.workflows import dispatch_workflow

router = APIRouter(tags=["execute"])

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
    "x-jentic-credential", "x-jentic-callback",
    # Host is set from the target URL
    "host",
}

# How we detect credentials for a given API host
# Looks up the api in the apis table by id (which is the scheme-stripped base URL)
# then finds matching credentials by api_id + scheme_name and injects them as HTTP headers.
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
            async with db.execute(
                "SELECT id FROM apis WHERE id=? OR id LIKE ?",
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
) -> tuple[dict[str, str], str | None, str | None]:
    """
    Return (headers_to_inject, api_id, credential_id) for the given upstream host.

    credential_id is the ID of the first credential used for injection — used by the
    caller to enforce per-credential policy rules.
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
            async with db.execute(
                "SELECT id FROM apis WHERE id=? OR id LIKE ?",
                (candidate, f"{candidate}%"),
            ) as cur:
                row = await cur.fetchone()
            if row:
                api_id = row[0]
                break

    _broker_log.debug("CRED LOOKUP: host=%r → api_id=%r (toolkit=%r alias=%r)", host, api_id, toolkit_id, alias)

    if not api_id:
        return {}, None, None

    # Get credentials bound to this toolkit + api
    creds = await vault.get_credentials_for_api(toolkit_id, api_id)
    _broker_log.debug("CRED LOOKUP: %d cred(s) for api_id=%r: %s", len(creds), api_id, [c.get("id") for c in creds])

    if not creds and toolkit_id:
        raise ValueError(
            f"No credentials found for '{api_id}' in toolkit '{toolkit_id}'. "
            f"Use POST /toolkits/{toolkit_id}/access-requests to request access."
        )

    if alias and creds:
        matched = [c for c in creds if c.get("id") == alias]
        if matched:
            _broker_log.debug("CRED LOOKUP: alias %r matched → using %r", alias, matched[0].get("id"))
            creds = matched
        else:
            _broker_log.warning("CRED LOOKUP: alias %r not found in %s — falling back to first cred", alias, [c.get("id") for c in creds])
        # If alias doesn't match any credential, fall through with all creds (best-effort)

    # Get merged security schemes (spec + confirmed overlays)
    from src.routers.overlays import get_merged_security_schemes
    schemes = await get_merged_security_schemes(api_id)

    if not schemes:
        # No schemes at all — nothing to inject
        return {}, api_id, creds[0]["id"] if creds else None

    headers = {}
    first_credential_id: str | None = None
    for cred in creds:
        scheme_name = cred.get("scheme_name")
        if not scheme_name:
            # No scheme_name stored on this credential — fall back to the
            # first (and usually only) scheme defined for this API.
            # Prefer basic over bearer when both exist (git HTTPS needs Basic auth).
            _basic_key = next((k for k, v in schemes.items() if v.get("type") == "http" and v.get("scheme", "").lower() == "basic"), None)
            scheme_name = _basic_key or next(iter(schemes), None)
        if not scheme_name:
            continue

        scheme = schemes.get(scheme_name, {})
        if not scheme:
            # Scheme name not found — fall back to the first available scheme
            scheme_name = next(iter(schemes), None)
            scheme = schemes.get(scheme_name, {}) if scheme_name else {}
        if not scheme:
            continue

        value = cred["value"]
        scheme_type = scheme.get("type", "")

        if not first_credential_id:
            first_credential_id = cred["id"]

        if scheme_type == "apiKey":
            location = scheme.get("in", "header")
            header_name = scheme.get("name", "X-API-Key")
            if location == "header":
                headers[header_name] = value
            elif location == "query":
                # Query params handled separately; store for URL building
                # For now log and skip — query auth needs URL modification
                pass
        elif scheme_type == "http":
            bearer_scheme = scheme.get("scheme", "bearer").lower()
            if bearer_scheme == "bearer":
                headers["Authorization"] = f"Bearer {value}"
            elif bearer_scheme == "basic":
                import base64 as _b64
                # BasicAuth encoding rules (data-driven, no API-specific logic):
                #
                # 1. If value contains ":" — treat as raw "username:password",
                #    base64-encode the whole thing directly.
                # 2. If the scheme carries x-jentic-basic-username — use it as
                #    the username: base64("{annotation}:{value}").
                #    e.g. GitHub overlay sets x-jentic-basic-username: "x-access-token"
                # 3. Fallback: base64(":{value}") — token as password, no username.
                #    Safe generic default; works for most API-key-as-password schemes.
                if ":" in value:
                    _raw = value
                elif "x-jentic-basic-username" in scheme:
                    _raw = f"{scheme['x-jentic-basic-username']}:{value}"
                else:
                    _raw = f":{value}"
                headers["Authorization"] = f"Basic {_b64.b64encode(_raw.encode()).decode()}"
        elif scheme_type == "oauth2":
            headers["Authorization"] = f"Bearer {value}"

    _broker_log.debug("CRED INJECT: api_id=%r injecting headers=%s using cred=%r", api_id, list(headers.keys()), first_credential_id)
    return headers, api_id, first_credential_id


async def _find_pipedream_credential_for_host(
    host: str,
    toolkit_id: str | None,
    alias: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (account_id, credential_id) for a Pipedream-managed credential in this toolkit.

    Pipedream credentials have scheme_name='pipedream_oauth' and their encrypted value
    IS the Pipedream account_id (apn_xxx). This bypasses the apis table lookup —
    Pipedream-connected APIs may not have a spec in the local catalog.

    If alias is specified, only the credential with that ID is considered.
    Returns (None, None) if no Pipedream credential is provisioned for this host+toolkit.
    """
    if not toolkit_id:
        return None, None
    from src.db import DEFAULT_TOOLKIT_ID
    async with get_db() as db:
        if alias:
            # Caller specified an exact credential — use it directly if it's Pipedream
            async with db.execute(
                "SELECT id, encrypted_value FROM credentials "
                "WHERE id=? AND scheme_name='pipedream_oauth'",
                (alias,),
            ) as cur:
                row = await cur.fetchone()
        elif toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                "SELECT id, encrypted_value FROM credentials "
                "WHERE api_id=? AND scheme_name='pipedream_oauth' LIMIT 1",
                (host,),
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute(
                """SELECT c.id, c.encrypted_value FROM credentials c
                   JOIN toolkit_credentials tc ON tc.credential_id = c.id
                   WHERE tc.toolkit_id=? AND c.api_id=? AND c.scheme_name='pipedream_oauth'
                   LIMIT 1""",
                (toolkit_id, host),
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


_BROKER_DESCRIPTION = (
    "Routes any HTTP request to the upstream API, injecting credentials automatically.\n\n"
    "URL shape: `/{upstream_host}/{path}` — e.g. `/api.stripe.com/v1/customers`\n\n"
    "All HTTP methods supported; Swagger UI shows GET as representative.\n\n"
    "**Headers:**\n"
    "- `X-Jentic-Simulate: true` — validate and preview the call without sending it\n"
    "- `X-Jentic-Credential: {alias}` — select a specific credential when multiple exist for an API\n"
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
    "/{target:path}",
    include_in_schema=True,
    tags=["execute"],
    summary="Broker — proxy a call to any registered API with automatic credential injection",
    description=_BROKER_DESCRIPTION,
    responses=_BROKER_RESPONSES,
    operation_id="broker_get",
)
async def broker_doc_stub(request: Request, target: str):
    """Documentation stub — delegates to the real broker handler."""
    return await broker(request, target)


@router.api_route(
    "/{target:path}",
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
    import os as _os
    _jentic_host = (
        _os.environ.get("JENTIC_PUBLIC_HOSTNAME")
        or "jentic-mini.home.seanblanchfield.com"  # default fallback
    )
    # Also detect self-referential calls via the request's Host header
    # (handles cases where the container doesn't have env vars set)
    _request_host = request.headers.get("host", "").split(":")[0]
    _is_self = (
        upstream_host == _jentic_host
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

    execution_id = str(uuid.uuid4())
    # toolkit_id is None for unauthenticated (anonymous) requests —
    # credential injection and policy checks are skipped in that case.
    toolkit_id: str | None = getattr(request.state, "toolkit_id", None)
    is_simulate = (
        getattr(request.state, "simulate", False)
        or request.headers.get("x-jentic-simulate", "").lower() == "true"
    )
    credential_alias = request.headers.get("x-jentic-credential")
    callback_url = request.headers.get("x-jentic-callback")

    # ── Prefer: wait=N for single broker calls ────────────────────────────────
    # Parsed here and threaded through to the async path below if the upstream
    # call takes too long.
    from src.utils import parse_prefer_wait
    prefer_wait = parse_prefer_wait(request.headers.get("prefer"))

    # ── Resolve credential IDs (no decryption) → policy check ────────────────
    # We resolve the api_id and credential IDs first — without decrypting —
    # so policy can be enforced before the vault is ever touched.
    # Denied requests never decrypt a credential.
    _api_id_for_host: str | None = None
    _resolved_cred_ids: list[str] = []
    try:
        _api_id_for_host, _resolved_cred_ids = await _resolve_credential_ids(
            host=upstream_host, toolkit_id=toolkit_id
        )
    except Exception:
        pass  # resolution failure handled below in full lookup

    if toolkit_id and _resolved_cred_ids:
        from src.routers.toolkits import check_credential_policy
        # Check against the first matched credential (primary)
        primary_cred_id = _resolved_cred_ids[0]
        try:
            allowed, reason = await check_credential_policy(
                credential_id=primary_cred_id,
                operation_id=f"{request.method}/{upstream_host}{upstream_path}",
                method=request.method,
                path=upstream_path,
            )
            if not allowed:
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
            pass  # policy check failure is non-fatal

    # body_bytes initialised here so the OAuthBroker fallback can read it
    # without a double-read; the main forward path reads it again below if empty.
    body_bytes: bytes = b""

    # ── Full credential lookup (with decryption) ──────────────────────────────
    try:
        inject_headers, api_id, credential_id = await _find_credential_for_host(
            host=upstream_host,
            path=upstream_path,
            toolkit_id=toolkit_id,
            alias=credential_alias,
        )
    except Exception as e:
        error_body = {"error": "CREDENTIAL_LOOKUP_FAILED", "message": str(e)}
        return Response(
            content=json.dumps(error_body),
            status_code=500,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
        )

    # ── Pipedream credential path ─────────────────────────────────────────────
    # If the vault lookup yielded no headers, check for an explicitly-provisioned
    # Pipedream credential (scheme_name='pipedream_oauth'). This path requires:
    #   1. POST /oauth-brokers/{id}/sync  — creates the credential in the vault
    #   2. POST /toolkits/{id}/credentials — explicitly provisions it to this toolkit
    # No implicit fallback. If no credential is provisioned, we fall through to
    # unauthenticated forwarding (or the request will fail upstream with 401).
    if not inject_headers:
        pd_account_id, pd_cred_id = await _find_pipedream_credential_for_host(
            upstream_host, toolkit_id, alias=credential_alias
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
                    pass  # policy check failure is non-fatal

            # Find the Pipedream broker instance and proxy using the credential's account_id
            from src.oauth_broker import registry as _oauth_registry
            _ext_user = request.headers.get("x-jentic-external-user-id", "default")
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
                    api_host=upstream_host,
                    upstream_path=upstream_path,
                    method=request.method,
                    headers=_fwd_hdrs,
                    body=body_bytes,
                    query_string=request.url.query,
                    external_user_id=_ext_user,
                )
                if _pd_resp is not None:
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
    # If the target host is ourselves, route to localhost to avoid an external
    # DNS round-trip. This is what makes jentic-in-jentic work inside Docker.
    import os as _os2
    _internal_port = int(_os2.environ.get("JENTIC_INTERNAL_PORT", "8900"))
    if _is_self:
        upstream_url = f"http://localhost:{_internal_port}{upstream_path}"
    else:
        upstream_url = f"https://{upstream_host}{upstream_path}"
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
                if upstream_async_flag:
                    await update_job(job_id, status="upstream_async", result=result,
                                     http_status=202, upstream_async=True, upstream_job_url=upstream_loc)
                elif resp.status_code < 400:
                    await update_job(job_id, status="complete", result=result, http_status=resp.status_code)
                else:
                    await update_job(job_id, status="failed", error=resp.text[:512], http_status=resp.status_code)
            except Exception as exc:
                await update_job(job_id, status="failed", error=str(exc))
            finally:
                _running_tasks.pop(job_id, None)

        task = asyncio.create_task(_broker_bg())
        _running_tasks[job_id] = task
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
        error_body = {
            "error": "UPSTREAM_TIMEOUT",
            "message": f"Upstream {upstream_host} did not respond within 60s",
        }
        return Response(
            content=json.dumps(error_body),
            status_code=504,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
        )
    except httpx.RequestError as e:
        error_body = {
            "error": "UPSTREAM_UNREACHABLE",
            "message": f"Could not reach {upstream_host}: {str(e)}",
        }
        return Response(
            content=json.dumps(error_body),
            status_code=502,
            media_type="application/json",
            headers={"X-Jentic-Error": "true", "X-Jentic-Execution-Id": execution_id},
        )

    # ── Build response — strip hop-by-hop, add Jentic trace headers ──────────
    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    response_headers["X-Jentic-Execution-Id"] = execution_id

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
                    "The credential value may be correct but the username format is wrong. "
                    "Research the correct BasicAuth username format for this API, then submit "
                    f"an overlay via POST /apis/{api_id}/overlays with the 'x-jentic-basic-username' "
                    "extension on the BasicAuth security scheme. Example: "
                    '{"overlay":"1.0.0","info":{"title":"BasicAuth username","version":"1.0.0"},'
                    '"actions":[{"target":"$","update":{"components":{"securitySchemes":{"BasicAuth":'
                    '{"type":"http","scheme":"basic","x-jentic-basic-username":"<username_here>"}}}}}]}'
                ),
                "action": f"POST /apis/{api_id}/overlays",
                "upstream_status": upstream_response.status_code,
                "upstream_body": upstream_response.text[:512],
            }
            response_headers["X-Jentic-Hint"] = "basic_auth_failure"
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

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
