"""Fernet-encrypted credential vault."""
import logging
import os
import re
import json as _json
import uuid
from urllib.parse import urlparse
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from src.db import get_db

_vault_log = logging.getLogger(__name__)

_KEY_FILE = Path(os.getenv("DB_PATH", "/app/data/jentic-mini.db")).parent / "vault.key"

_COMMON_WORDS = {
    "api", "key", "token", "secret", "auth", "oauth",
    "credential", "credentials", "access", "the", "a", "an",
}


def _parse_route(route: str) -> tuple[str, str]:
    """Split a route string into (host, path_prefix).

    Examples::

        "api.groq.com/openai"  → ("api.groq.com", "/openai")
        "techpreneurs.ie"      → ("techpreneurs.ie", "/")
        "10.0.0.3:8123/api"   → ("10.0.0.3:8123", "/api")
    """
    r = route
    if r.startswith("https://"):
        r = r[8:]
    elif r.startswith("http://"):
        r = r[7:]
    if "/" in r:
        host, rest = r.split("/", 1)
        return host, "/" + rest
    return r, "/"


async def _resolve_server_url(api_id: str | None, server_variables: dict[str, str] | None) -> str | None:
    """Resolve the canonical server URL for api_id, substituting any OpenAPI server
    template variables (e.g. {defaultHost}) with values from server_variables.

    Returns the resolved URL string (e.g. 'https://10.0.0.2:9443/api',
    'https://techpreneurs.ie/') suitable for passing directly to _parse_route.
    Returns None if no base_url is available in the spec.
    """
    if not api_id:
        return None
    async with get_db() as db:
        async with db.execute("SELECT base_url FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        _vault_log.debug("_resolve_server_url: no base_url for api_id=%r", api_id)
        return None
    resolved = row[0]
    # Substitute any OpenAPI server template variables (e.g. {defaultHost})
    if server_variables:
        template_vars = re.findall(r"\{([^}]+)\}", resolved)
        for var in template_vars:
            if var in server_variables:
                resolved = resolved.replace(f"{{{var}}}", server_variables[var])
    # If unresolved template vars remain, the URL is not fully qualified — skip
    if "{" in resolved:
        _vault_log.debug("_resolve_server_url: unresolved template vars in %r — skipping", resolved)
        return None
    _vault_log.debug("_resolve_server_url: api_id=%r resolved=%r", api_id, resolved)
    return resolved


def _credential_slug(api_id: str | None, label: str) -> str:
    """Generate a semantic, URL-safe credential ID from api_id + label.

    Strategy:
      - Start with api_id (e.g. "api.elevenlabs.io")
      - Tokenize label; strip tokens appearing in api_id or that are common words
      - Slugify the remainder and append with '-' separator
      - If nothing remains, use api_id alone
      - If no api_id, slugify the label directly

    Examples:
      api.elevenlabs.io + "ElevenLabs API Key"  → "api.elevenlabs.io"
      api.github.com    + "GitHub PAT"          → "api.github.com-pat"
      api.openai.com    + "OpenAI Org Key"      → "api.openai.com-org"
      api.stripe.com    + "Stripe Live Secret"  → "api.stripe.com-live"
    """
    if not api_id:
        slug = re.sub(r"[^a-z0-9.-]+", "-", label.lower()).strip("-")
        return slug or "credential"

    api_tokens = set(re.split(r"[./\-_]", api_id.lower())) | _COMMON_WORDS
    label_parts = re.split(r"[\s\-_./]+", label.lower())
    remainder = [p for p in label_parts if p and p not in api_tokens]

    if remainder:
        suffix = re.sub(r"[^a-z0-9]+", "-", "-".join(remainder)).strip("-")
        return f"{api_id}-{suffix}" if suffix else api_id
    return api_id


def _fernet() -> Fernet:
    key = os.getenv("JENTIC_VAULT_KEY", "")
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            pass  # fall through to auto-generate
    # Auto-generate and persist a key on first use
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text().strip()
    else:
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key().decode()
        _KEY_FILE.write_text(key)
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt credential") from e


async def derive_scheme_for_credential(
    api_id: str | None,
    auth_type: str | None,
    identity: str | None,
) -> dict | None:
    """Derive the scheme blob for a credential from its API description.

    This replicates the logic in migration 0007 at credential write-time so that
    all new credentials are self-describing from the moment they are created.
    Returns None when derivation is not possible (no api_id, no spec, pipedream_oauth).
    """
    if not api_id or not auth_type or auth_type == "pipedream_oauth":
        return None

    import base64 as _b64

    if auth_type in ("bearer", "oauth2"):
        return {"in": "header", "name": "Authorization", "prefix": "Bearer "}

    if auth_type == "basic":
        return {"in": "header", "name": "Authorization", "prefix": "Basic ", "encode": "base64"}

    if auth_type == "apiKey":
        try:
            from src.routers.apis import load_api_desc
            doc = await load_api_desc(api_id, include_pending=True)
        except Exception:
            return None
        if not doc:
            return None
        schemes = doc.get("components", {}).get("securitySchemes", {}) or doc.get("securityDefinitions", {})
        if not schemes:
            return None

        # Check for compound Secret+Identity pattern first
        secret_s = schemes.get("Secret")
        identity_s = schemes.get("Identity")
        if secret_s and identity_s:
            return {
                "secret": {"in": secret_s.get("in", "header"), "name": secret_s["name"]},
                "identity": {"in": identity_s.get("in", "header"), "name": identity_s["name"]},
            }

        # http bearer takes precedence over apiKey header schemes when identity not set
        http_bearer = next(
            (v for v in schemes.values()
             if v.get("type") == "http" and v.get("scheme", "").lower() not in ("basic", "digest")),
            None,
        )
        if http_bearer and not identity:
            return {"in": "header", "name": "Authorization", "prefix": "Bearer "}

        # http basic
        http_basic = next(
            (v for v in schemes.values()
             if v.get("type") == "http" and v.get("scheme", "").lower() == "basic"),
            None,
        )
        if http_basic:
            return {"in": "header", "name": "Authorization", "prefix": "Basic ", "encode": "base64"}

        # apiKey header schemes
        apikey_header = {k: v for k, v in schemes.items() if v.get("type") == "apiKey" and v.get("in") == "header"}
        if not apikey_header:
            return None

        # With identity — prefer Secret scheme
        if identity:
            s = apikey_header.get("Secret") or next(iter(apikey_header.values()))
            return {"in": "header", "name": s["name"]}

        # Single scheme
        if len(apikey_header) == 1:
            s = next(iter(apikey_header.values()))
            return {"in": "header", "name": s["name"]}

        # Multiple schemes — keyword scoring to pick the canonical one
        _IDENTITY_KEYWORDS = frozenset(["user", "username", "login", "email", "account"])
        non_identity = {k: v for k, v in apikey_header.items()
                        if not any(kw in k.lower() or kw in v.get("name", "").lower()
                                   for kw in _IDENTITY_KEYWORDS)}
        candidates = non_identity or apikey_header
        # Prefer the most specific name (longest header name tends to be less generic)
        best = max(candidates.values(), key=lambda v: len(v.get("name", "")))
        return {"in": "header", "name": best["name"]}

    return None


async def create_credential(
    label: str,
    value: str,
    api_id: str | None = None,
    env_var: str | None = None,  # legacy param, now derived from cid if omitted
    scheme_name: str | None = None,  # legacy param name kept for call-site compat; stored as auth_type
    identity: str | None = None,
    server_variables: dict[str, str] | None = None,
    scheme: dict | None = None,
    routes: list[str] | None = None,
) -> dict:
    base_slug = _credential_slug(api_id, label)
    enc = encrypt(value)

    async with get_db() as db:
        # Collision-safe semantic ID
        cid = base_slug
        suffix_n = 2
        while True:
            async with db.execute("SELECT id FROM credentials WHERE id=?", (cid,)) as cur:
                if not await cur.fetchone():
                    break
            cid = f"{base_slug}-{suffix_n}"
            suffix_n += 1

        # env_var must also be unique — derive from cid (already deduplicated above)
        # If caller passed an explicit env_var, use it; otherwise derive from cid
        import re as _re
        if not env_var:
            env_var = _re.sub(r"[^a-zA-Z0-9]+", "_", cid).strip("_").upper()

        import json as _json
        sv_json = _json.dumps(server_variables) if server_variables else None

        # Derive routes if not explicitly provided
        if routes is None:
            resolved_host = await _resolve_server_url(api_id, server_variables)
            if resolved_host:
                routes = [resolved_host]
            elif api_id:
                routes = [api_id]

        # Auto-derive scheme if not explicitly provided
        if scheme is None:
            scheme = await derive_scheme_for_credential(api_id, scheme_name, identity)
        scheme_json = _json.dumps(scheme) if scheme else None

        await db.execute(
            "INSERT INTO credentials (id, label, env_var, encrypted_value, api_id, auth_type, identity, server_variables, scheme) VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, label, env_var, enc, api_id, scheme_name, identity, sv_json, scheme_json),
        )

        # Insert into credential_routes
        if routes:
            for route in routes:
                host, path_prefix = _parse_route(route)
                await db.execute(
                    "INSERT OR IGNORE INTO credential_routes (credential_id, host, path_prefix) VALUES (?,?,?)",
                    (cid, host, path_prefix),
                )

        await db.commit()
        row = await _fetch_credential_row(db, cid)
    return _row_to_dict(row)


# Explicit column list — insulates _row_to_dict from schema churn.
# If a column is added/removed, only this query and _row_to_dict need updating.
_CREDENTIAL_COLS = (
    "id, label, created_at, updated_at, api_id, auth_type, identity, server_variables, scheme"
)

async def _fetch_credential_row(db, cid: str):
    """Fetch a credential row plus its routes as a synthetic last column."""
    async with db.execute(
        f"SELECT {_CREDENTIAL_COLS} FROM credentials WHERE id=?", (cid,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    async with db.execute(
        "SELECT host, path_prefix FROM credential_routes WHERE credential_id=? ORDER BY length(path_prefix) DESC",
        (cid,)
    ) as cur:
        route_rows = await cur.fetchall()
    # Synthesise routes list: host + path_prefix (strip trailing / if path_prefix is /)
    routes = []
    for host, pp in route_rows:
        routes.append(host + pp if pp != "/" else host)
    return (*row, routes)  # append routes as the final synthetic element


async def get_credential(cid: str) -> dict | None:
    """Fetch a single credential by ID and return its full metadata dict (no value)."""
    async with get_db() as db:
        row = await _fetch_credential_row(db, cid)
    return _row_to_dict(row) if row else None


async def patch_credential(cid: str, label: str | None, value: str | None,
                           api_id: str | None = None, scheme_name: str | None = None,
                           identity: str | None = None,
                           server_variables: dict[str, str] | None = None,
                           scheme: dict | None = None,
                           routes: list[str] | None = None) -> dict | None:
    async with get_db() as db:
        if label:
            await db.execute("UPDATE credentials SET label=?, updated_at=unixepoch() WHERE id=?", (label, cid))
        if value:
            enc = encrypt(value)
            await db.execute("UPDATE credentials SET encrypted_value=?, updated_at=unixepoch() WHERE id=?", (enc, cid))
        if api_id is not None:
            await db.execute("UPDATE credentials SET api_id=?, updated_at=unixepoch() WHERE id=?", (api_id, cid))
        if scheme_name is not None:
            await db.execute("UPDATE credentials SET auth_type=?, updated_at=unixepoch() WHERE id=?", (scheme_name, cid))
        if identity is not None:
            await db.execute("UPDATE credentials SET identity=?, updated_at=unixepoch() WHERE id=?", (identity, cid))
        if server_variables is not None:
            sv_json = _json.dumps(server_variables) if server_variables else None
            await db.execute("UPDATE credentials SET server_variables=?, updated_at=unixepoch() WHERE id=?", (sv_json, cid))

        # Update scheme
        if scheme is not None:
            await db.execute("UPDATE credentials SET scheme=?, updated_at=unixepoch() WHERE id=?", (_json.dumps(scheme), cid))
        elif any(x is not None for x in [api_id, scheme_name, identity]):
            async with db.execute("SELECT api_id, auth_type, identity FROM credentials WHERE id=?", (cid,)) as _scur:
                _srow = await _scur.fetchone()
            if _srow:
                _derived = await derive_scheme_for_credential(
                    api_id if api_id is not None else _srow[0],
                    scheme_name if scheme_name is not None else _srow[1],
                    identity if identity is not None else _srow[2],
                )
                if _derived:
                    await db.execute("UPDATE credentials SET scheme=?, updated_at=unixepoch() WHERE id=?", (_json.dumps(_derived), cid))

        # Update credential_routes
        if routes is not None:
            # Explicit routes override — replace all existing routes
            await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cid,))
            for route in routes:
                host, path_prefix = _parse_route(route)
                await db.execute(
                    "INSERT OR IGNORE INTO credential_routes (credential_id, host, path_prefix) VALUES (?,?,?)",
                    (cid, host, path_prefix),
                )
        elif server_variables is not None or api_id is not None:
            # Recompute routes from updated server_variables/api_id
            async with db.execute("SELECT api_id, server_variables FROM credentials WHERE id=?", (cid,)) as _cur:
                _row = await _cur.fetchone()
            if _row:
                _current_api_id = api_id if api_id is not None else _row[0]
                _current_sv_raw = _json.dumps(server_variables) if server_variables is not None else _row[1]
                _current_sv = _json.loads(_current_sv_raw) if _current_sv_raw else None
                computed_host = await _resolve_server_url(_current_api_id, _current_sv)
                new_route = computed_host or _current_api_id
                if new_route:
                    await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cid,))
                    host, path_prefix = _parse_route(new_route)
                    await db.execute(
                        "INSERT OR IGNORE INTO credential_routes (credential_id, host, path_prefix) VALUES (?,?,?)",
                        (cid, host, path_prefix),
                    )

        await db.commit()
        row = await _fetch_credential_row(db, cid)
    return _row_to_dict(row) if row else None


async def delete_credential(cid: str) -> bool:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM credentials WHERE id=?", (cid,))
        await db.commit()
    return cur.rowcount > 0



async def get_credential_value(db, vault_id: str) -> str | None:
    """
    Return the decrypted value for a credential by UUID.
    Used by auth_override to resolve vault_id references.
    """
    async with db.execute(
        "SELECT encrypted_value FROM credentials WHERE id=?", (vault_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return decrypt(row[0])
async def get_credential_ids_for_route(toolkit_id: str, host: str, path: str = "/") -> list[str]:
    """Return credential IDs matching host+path, longest path_prefix first.

    O(log N) host index lookup, then a small linear scan over path_prefix rows.
    No decryption. Used for policy checks.
    """
    from src.db import DEFAULT_TOOLKIT_ID
    req_path = path if path.startswith("/") else "/" + path

    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                "SELECT credential_id, path_prefix FROM credential_routes WHERE host=?",
                (host,),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT cr.credential_id, cr.path_prefix
                   FROM credential_routes cr
                   JOIN toolkit_credentials tc ON cr.credential_id = tc.credential_id
                   WHERE cr.host=? AND tc.toolkit_id=?""",
                (host, toolkit_id),
            ) as cur:
                rows = await cur.fetchall()

    candidates = [
        (cid, pp) for cid, pp in rows
        if req_path.startswith(pp if pp.endswith("/") else pp + "/")
        or req_path == pp
        or pp == "/"
    ]
    seen: set[str] = set()
    result: list[str] = []
    for cid, _ in sorted(candidates, key=lambda x: len(x[1]), reverse=True):
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


async def get_credentials_for_route(toolkit_id: str, host: str, path: str) -> list[dict]:
    """Return full credential dicts (with decrypted value) for the given host+path.

    Calls get_credential_ids_for_route for the ID list (path matching, no decrypt),
    then fetches and decrypts only the matched credentials.
    Results are in longest path_prefix first order.
    """
    ids = await get_credential_ids_for_route(toolkit_id, host, path)
    if not ids:
        return []

    placeholders = ",".join("?" * len(ids))
    async with get_db() as db:
        async with db.execute(
            f"""SELECT id, encrypted_value, auth_type, identity, server_variables, scheme
                FROM credentials WHERE id IN ({placeholders})""",
            ids,
        ) as cur:
            rows = await cur.fetchall()

    # Preserve the longest-match order from get_credential_ids_for_route
    row_by_id = {row[0]: row for row in rows}
    result = []
    for cid in ids:
        row = row_by_id.get(cid)
        if not row:
            continue
        cid, enc_val, auth_type, identity, sv_raw, scheme_raw = row
        try:
            server_variables = _json.loads(sv_raw) if sv_raw else None
        except Exception:
            server_variables = None
        result.append({
            "id": cid,
            "value": decrypt(enc_val),
            "auth_type": auth_type,
            "identity": identity,
            "server_variables": server_variables,
            "scheme": _json.loads(scheme_raw) if scheme_raw else None,
        })
    return result


def _row_to_dict(row) -> dict:
    # Columns from _CREDENTIAL_COLS (explicit SELECT — immune to schema churn):
    # 0:id, 1:label, 2:created_at, 3:updated_at, 4:api_id, 5:auth_type,
    # 6:identity, 7:server_variables, 8:scheme
    # routes is synthetic — appended by _fetch_credential_row as the last element
    sv_raw = row[7] if len(row) > 7 else None
    try:
        server_variables = _json.loads(sv_raw) if sv_raw else None
    except Exception:
        server_variables = None
    scheme_raw = row[8] if len(row) > 8 else None
    # routes is the synthetic last element added by _fetch_credential_row
    routes = row[-1] if len(row) > 9 and isinstance(row[-1], list) else None
    return {
        "id": row[0],
        "label": row[1],
        "created_at": row[2],
        "updated_at": row[3],
        "api_id": row[4] if len(row) > 4 else None,
        "auth_type": row[5] if len(row) > 5 else None,
        "identity": row[6] if len(row) > 6 else None,
        "server_variables": server_variables,
        "scheme": _json.loads(scheme_raw) if scheme_raw else None,
        "routes": routes,
    }
