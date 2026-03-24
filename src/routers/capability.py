"""
GET /inspect/{capability_id:path} — full detail for an operation or workflow.

Capability IDs use the format:  METHOD/host/path
e.g.:  GET/api.intercom.io/admins/activity_logs
       POST/api.stripe.com/v1/payment_intents
       POST/{jentic_hostname}/workflows/summarise-latest-topics

No scheme (always https), no colon, no space, no double-slash.
The method is always a valid HTTP verb; a hostname can never start with one,
so the split is unambiguous: first path segment = method, rest = host/path.

Workflow IDs are detected by matching the Jentic hostname + /workflows/ path.
The backend transparently handles both types — callers need not distinguish.
"""
import json
import re
import yaml
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from src.db import get_db
from src.config import JENTIC_PUBLIC_HOSTNAME

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_refs(schema: Any, doc: dict, depth: int = 0) -> Any:
    if depth > 6 or not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            parts = ref.lstrip("#/").split("/")
            resolved = doc
            for part in parts:
                resolved = resolved.get(part, {})
            return _resolve_refs(resolved, doc, depth + 1)
        return schema
    result = {k: _resolve_refs(v, doc, depth + 1) if isinstance(v, (dict, list)) else v
              for k, v in schema.items()}
    if "items" in schema:
        result["items"] = _resolve_refs(schema["items"], doc, depth + 1)
    return result


def _translate_auth(security_schemes: dict, security_requirements: list) -> list[dict]:
    result = []
    for req in security_requirements:
        for scheme_name, scopes in req.items():
            scheme = security_schemes.get(scheme_name, {})
            s_type = scheme.get("type", "")
            entry: dict = {"scheme": scheme_name}
            if s_type == "apiKey":
                entry["type"] = "api_key"
                entry["in"] = scheme.get("in", "header")
                entry["name"] = scheme.get("name", scheme_name)
                entry["instruction"] = f"Set {scheme.get('in','header')} `{scheme.get('name', scheme_name)}`"
            elif s_type == "http":
                http_scheme = scheme.get("scheme", "bearer").lower()
                entry["type"] = f"http_{http_scheme}"
                if http_scheme == "bearer":
                    entry["instruction"] = "Set header `Authorization: Bearer <token>`"
                else:
                    entry["instruction"] = f"Set header `Authorization: {http_scheme.capitalize()} <credentials>`"
            elif s_type == "oauth2":
                entry["type"] = "oauth2"
                flows = scheme.get("flows", {})
                entry["flows"] = list(flows.keys())
                entry["scopes"] = scopes
                entry["instruction"] = f"OAuth2 ({', '.join(flows.keys())}); required scopes: {scopes or 'none'}"
            else:
                entry["type"] = s_type
                entry["instruction"] = f"Auth scheme '{scheme_name}' (type: {s_type})"
            result.append(entry)
    return result


def _extract_parameters(op: dict, path_item: dict, doc: dict) -> dict:
    all_params = list(path_item.get("parameters", [])) + list(op.get("parameters", []))
    by_location: dict = {}
    for param in all_params:
        param = _resolve_refs(param, doc)
        loc = param.get("in", "query")
        by_location.setdefault(loc, []).append({
            "name": param.get("name"),
            "required": param.get("required", False),
            "description": param.get("description"),
            "schema": _resolve_refs(param.get("schema", {}), doc),
        })
    body = op.get("requestBody", {})
    if body:
        body = _resolve_refs(body, doc)
        content = body.get("content", {})
        for media_type, media_obj in content.items():
            schema = _resolve_refs(media_obj.get("schema", {}), doc)
            by_location["body"] = {
                "required": body.get("required", False),
                "description": body.get("description"),
                "media_type": media_type,
                "schema": schema,
            }
            break
    return by_location


def _extract_response_schema(op: dict, doc: dict) -> dict | None:
    responses = op.get("responses", {})
    for code in ("200", "201", "202", "default"):
        resp = responses.get(code)
        if resp:
            resp = _resolve_refs(resp, doc)
            content = resp.get("content", {})
            for media_type, media_obj in content.items():
                schema = _resolve_refs(media_obj.get("schema", {}), doc)
                return {"status": code, "media_type": media_type, "schema": schema}
    return None


# ── Capability ID parsing ─────────────────────────────────────────────────────

_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
_CAP_RE = re.compile(
    r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)/(.+)$",
    re.IGNORECASE,
)


def _parse_capability_id(capability_id: str) -> tuple[str, str]:
    """Parse 'METHOD/host/path' into (method, 'https://host/path').

    Split on first slash: left is the HTTP method, right is host+path.
    A hostname can never start with a valid HTTP verb, so the split is unambiguous.
    """
    m = _CAP_RE.match(capability_id)
    if not m:
        raise ValueError(f"Invalid capability id: {capability_id!r}. Expected METHOD/host/path")
    method = m.group(1).upper()
    host_path = m.group(2)
    return method, f"https://{host_path}"


# ── Workflow capability helper ────────────────────────────────────────────────

async def _get_workflow_capability(slug: str, capability_id: str, toolkit_id: str | None) -> dict:
    """Return agent-facing detail for a workflow.

    Design intent: an agent should be able to read this response and know
    everything it needs to call the workflow successfully. Specifically:
    - What inputs to provide (only what the client supplies — broker-managed
      credentials are invisible; they're injected automatically)
    - What outputs to expect
    - What errors can occur
    - Where to find the full Arazzo definition if it wants the technical spec

    We do NOT expose: step internals, raw operationIds, security scheme wiring,
    broker credential config. Those are implementation details.
    """
    async with get_db() as db:
        async with db.execute(
            """SELECT slug, name, description, arazzo_path, input_schema,
                      steps_count, involved_apis, created_at
               FROM workflows WHERE slug=?""",
            (slug,),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, f"Workflow not found: {slug}")

    (db_slug, name, description, arazzo_path, input_schema_str,
     steps_count, involved_apis_str, created_at) = row

    # Load Arazzo doc for authoritative inputs, outputs, step info
    arazzo_file = Path(arazzo_path)
    doc: dict = {}
    if arazzo_file.exists():
        raw = arazzo_file.read_text()
        doc = yaml.safe_load(raw) if str(arazzo_file).endswith((".yaml", ".yml")) else json.loads(raw)

    workflows_list = doc.get("workflows", [])
    wf = next((w for w in workflows_list if w.get("workflowId") == slug), {}) or (workflows_list[0] if workflows_list else {})

    # ── Inputs: authoritative from Arazzo file; filter out broker-managed creds ──
    # Credentials stored in the vault are injected transparently by the broker.
    # We detect broker-managed params by checking: are they only used as explicit
    # header/query/cookie params passed directly from inputs in every step?
    # A simpler heuristic: if a param name matches a known credential env_var
    # label (case-insensitive), it's broker-managed. But the cleanest approach
    # is to use the Arazzo file's own inputs definition — if it was registered
    # cleanly (without broker-era legacy params), it's already correct.
    arazzo_inputs = wf.get("inputs", {})

    # Also load from DB schema as fallback, but prefer Arazzo file
    inputs_schema = arazzo_inputs or (json.loads(input_schema_str) if input_schema_str else {})

    # ── Outputs: from Arazzo workflow outputs ──
    raw_outputs = wf.get("outputs", {})
    # Outputs are Arazzo runtime expressions like "$steps.fetch-topics.outputs.topics"
    # Strip the expression and just expose the output key names with a description hint
    outputs = {}
    for key, expr in raw_outputs.items():
        # Derive a human-readable hint from the expression path
        parts = str(expr).split(".")
        hint = parts[-1] if parts else key  # e.g. "topics", "summary", "model_used"
        outputs[key] = hint

    # ── Errors: derive from the APIs involved in this workflow ──
    # Standard HTTP error taxonomy for broker-executed workflows
    errors = [
        {"status": 401, "description": "A required credential is missing or has expired. Check toolkit credentials for the APIs involved."},
        {"status": 403, "description": "Insufficient permissions — either the credential lacks scope, or a toolkit policy is blocking the operation."},
        {"status": 400, "description": "Invalid request — check that all required inputs are provided and correctly typed."},
        {"status": 422, "description": "Validation error in a workflow step — the request was structurally invalid for one of the APIs."},
        {"status": 429, "description": "Rate limit hit on one of the upstream APIs. Retry after a delay."},
        {"status": 502, "description": "An upstream API returned an unexpected response. The workflow step may need updated inputs or the API may be unavailable."},
    ]

    involved_apis = json.loads(involved_apis_str) if involved_apis_str else []

    workflow_url = f"https://{JENTIC_PUBLIC_HOSTNAME}/workflows/{slug}"
    encoded_id = quote(capability_id, safe="")

    result: dict = {
        "type": "workflow",
        "id": capability_id,
        "name": name,
        "description": description,
        # What the client must/can provide. Broker handles all credential injection.
        "inputs": inputs_schema,
        # Keys the workflow returns on success
        "outputs": outputs,
        # Common errors the client should handle
        "errors": errors,
        # APIs this workflow calls (informational)
        "apis": involved_apis,
        "_links": {
            "self": f"/inspect/{encoded_id}",
            "execute": f"POST /{JENTIC_PUBLIC_HOSTNAME}/workflows/{slug}",
            # Full Arazzo definition for those who want the technical spec
            "definition": f"/workflows/{slug}",
        },
    }
    return {k: v for k, v in result.items() if v is not None}


# ── Route ─────────────────────────────────────────────────────────────────────

_CAPABILITY_CONTENT_TYPES = {
    "application/json":       {"schema": {"type": "object", "description": "Structured JSON with resolved schemas"}},
    "text/markdown":          {"schema": {"type": "string", "description": "LLM-friendly prose description"}},
    "application/openapi+yaml": {"schema": {"type": "string", "description": "Filtered, dereferenced OpenAPI fragment"}},
}

@router.get(
    "/inspect/{capability_id:path}",
    summary="Inspect a capability — get full schema, auth, and parameters before calling",
    responses={
        200: {
            "description": "Full capability detail — format controlled by Accept header.",
            "content": _CAPABILITY_CONTENT_TYPES,
        }
    },
)
async def get_capability(
    capability_id: str,
    request: Request,
    toolkit_id: str | None = Query(None, description="Pass to include credential status for this toolkit"),
):
    """Returns everything needed to call an operation or workflow: resolved parameter schema
    (all $refs inlined), response schema, auth translated to concrete header instructions,
    API context (name, description, tag descriptions), and HATEOAS _links (execute, upstream).

    Capability id format: METHOD/host/path — e.g. GET/api.stripe.com/v1/customers
    or POST/{jentic_hostname}/workflows/summarise-latest-topics.
    Pass ?toolkit_id=... to check whether credentials are configured for that toolkit.
    Accept: text/markdown returns a compact LLM-friendly format.
    Accept: application/openapi+yaml returns the raw OpenAPI operation snippet.
    """
    try:
        method, full_url = _parse_capability_id(capability_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # ── Workflow detection ────────────────────────────────────────────────────
    # Workflow capability IDs: POST/{jentic_hostname}/workflows/{slug}
    # Detect by checking the host portion after the method prefix.
    _wf_re = re.compile(
        rf"^POST/{re.escape(JENTIC_PUBLIC_HOSTNAME)}/workflows/(.+)$", re.IGNORECASE
    )
    _wf_match = _wf_re.match(capability_id)
    if _wf_match:
        slug = _wf_match.group(1)
        return await _get_workflow_capability(slug, capability_id, toolkit_id)

    async with get_db() as db:
        async with db.execute(
            """SELECT o.id, o.api_id, o.operation_id, o.jentic_id, o.method, o.path,
                      o.summary, o.description,
                      a.spec_path, a.base_url, a.name, a.description
               FROM operations o JOIN apis a ON o.api_id = a.id
               WHERE o.jentic_id = ?""",
            (capability_id,),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(404, f"Capability not found: {capability_id}")

    (_, api_id, operation_id, jid, op_method, path,
     summary, description, spec_path, base_url, api_name, api_description) = row

    spec_file = Path(spec_path) if spec_path else None
    doc: dict = {}
    op_spec: dict = {}
    path_item: dict = {}
    if spec_file and spec_file.exists():
        raw = spec_file.read_text()
        doc = yaml.safe_load(raw) if str(spec_file).endswith((".yaml", ".yml")) else json.loads(raw)
        path_item = doc.get("paths", {}).get(path, {})
        op_spec = path_item.get(op_method.lower(), {}) if op_method else {}

    info = doc.get("info", {})
    all_tags = {t["name"]: t for t in doc.get("tags", []) if "name" in t}
    op_tags = op_spec.get("tags", [])
    tag_descriptions = [
        {"tag": t, "description": all_tags[t].get("description")}
        for t in op_tags if t in all_tags and all_tags[t].get("description")
    ]

    security_schemes = doc.get("components", {}).get("securitySchemes", {})
    global_security = doc.get("security", [])
    op_security = op_spec.get("security", global_security)
    auth = _translate_auth(security_schemes, op_security)

    parameters = _extract_parameters(op_spec, path_item, doc) if op_spec else {}
    response_schema = _extract_response_schema(op_spec, doc) if op_spec else None

    servers = doc.get("servers", [])
    server_url = base_url or (servers[0].get("url") if servers else None)

    credentials = None
    if toolkit_id:
        async with get_db() as db:
            async with db.execute(
                """SELECT c.id, c.label FROM credentials c
                   JOIN toolkit_credentials cc ON cc.credential_id = c.id
                   WHERE cc.toolkit_id = ?""",
                (toolkit_id,),
            ) as cur:
                creds = await cur.fetchall()
        credentials = (
            {"status": "configured",
             "available": [{"id": c[0], "label": c[1]} for c in creds]}
            if creds else {"status": "not_configured"}
        )

    encoded_id = quote(jid, safe="")
    broker_url = f"/{api_id}{path}" if api_id and path else None
    links: dict = {
        "self": f"/inspect/{jid}",
        "execute": broker_url or jid,
    }
    if server_url and path:
        links["upstream"] = f"{server_url}{path}"

    result: dict = {
        "id": jid,
        "method": op_method,
        "url": f"{server_url}{path}" if server_url and path else jid,
        "name": op_spec.get("operationId") or summary,
        "summary": summary,
        "description": op_spec.get("description") or description,
        "api": {k: v for k, v in {
            "id": api_id,
            "name": info.get("title") or api_name,
            "version": info.get("version"),
            "description": info.get("description") or api_description,
            "tag_descriptions": tag_descriptions or None,
        }.items() if v is not None},
        "parameters": parameters or None,
        "response_schema": response_schema,
        "auth": auth or None,
        "server": server_url,
        "_links": links,
    }
    if credentials is not None:
        result["credentials"] = credentials

    result["api"] = {k: v for k, v in result["api"].items() if v is not None}
    result = {k: v for k, v in result.items() if v is not None}

    # ── Format negotiation ────────────────────────────────────────────────────
    accept = (request.headers.get("accept", "") if request else "") or "application/json"

    if "text/markdown" in accept:
        params_md = ""
        params = result.get("parameters")
        if params and isinstance(params, dict):
            lines = []
            for loc, items in params.items():
                if loc == "body" and isinstance(items, dict):
                    schema = items.get("schema", {})
                    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
                    req = schema.get("required", []) if isinstance(schema, dict) else []
                    for pname, pschema in list(props.items())[:8]:
                        req_mark = " *(required)*" if pname in req else ""
                        ptype = pschema.get("type", "any") if isinstance(pschema, dict) else "any"
                        pdesc = pschema.get("description", "") if isinstance(pschema, dict) else ""
                        lines.append(f"  - `{pname}` ({ptype}, body){req_mark}: {pdesc}".rstrip(": "))
                elif isinstance(items, list):
                    for p in items[:6]:
                        req_mark = " *(required)*" if p.get("required") else ""
                        ptype = p.get("schema", {}).get("type", "any") if isinstance(p.get("schema"), dict) else "any"
                        lines.append(f"  - `{p.get('name')}` ({ptype}, {loc}){req_mark}: {p.get('description','') or ''}".rstrip(": "))
            if lines:
                params_md = "\n**Parameters:**\n" + "\n".join(lines)
        api_ctx = result.get("api", {})
        auth_md = ""
        auth_val = result.get("auth")
        if auth_val:
            auth_list = auth_val if isinstance(auth_val, list) else [auth_val]
            auth_lines = [
                f"`{a.get('header','?')}: {a.get('format','...')}`"
                for a in auth_list if isinstance(a, dict)
            ]
            if auth_lines:
                auth_md = f"\n**Auth:** {', '.join(auth_lines)}"
        md = (
            f"## {result.get('name') or result.get('summary')}\n\n"
            f"`{result['id']}`\n\n"
            f"{result.get('description') or ''}\n"
            f"{params_md}{auth_md}\n\n"
            f"**API:** {api_ctx.get('name','')} {('— ' + api_ctx.get('description',''))[:120] if api_ctx.get('description') else ''}\n\n"
            f"**Execute:** `https://exec.jentic.com/{result['id'].split('/', 1)[1] if '/' in result.get('id','') else result.get('url','')}`"
        )
        return Response(content=md, media_type="text/markdown")

    if "application/openapi+yaml" in accept:
        # Return a filtered OpenAPI fragment for this operation
        api_ctx = result.get("api", {})
        op_fragment = {
            "openapi": "3.0.0",
            "info": {"title": api_ctx.get("name", "API"), "version": api_ctx.get("version", "")},
            "paths": {
                path: {
                    op_method.lower(): {
                        "summary": result.get("summary"),
                        "description": result.get("description"),
                        "operationId": result.get("name"),
                        "parameters": [],
                        "requestBody": (
                            {"content": {"application/json": {"schema": result["parameters"]}}}
                            if result.get("parameters") and op_method.upper() in ("POST", "PUT", "PATCH")
                            else None
                        ),
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {"application/json": {"schema": result.get("response_schema", {})}},
                            }
                        },
                    }
                }
            },
        }
        # Clean None values
        op_fragment["paths"][path][op_method.lower()] = {
            k: v for k, v in op_fragment["paths"][path][op_method.lower()].items() if v is not None
        }
        return Response(
            content=yaml.dump(op_fragment, default_flow_style=False, allow_unicode=True),
            media_type="application/openapi+yaml",
        )

    return result
