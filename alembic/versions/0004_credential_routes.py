"""Add server_variables, scheme, and credential_routes to credentials.

server_variables: JSON object mapping OpenAPI server URL template variable
                  names to resolved values. Used by the broker to rewrite
                  host/base-path at routing time for self-hosted APIs.
                  Example: {"host": "forum.acme.com", "port": "443"}

scheme: JSON blob describing how to inject the credential value into upstream
        requests. Makes credentials self-describing so the broker does not need
        to load the API spec at proxy time.
        Example: {"in": "header", "name": "Authorization", "prefix": "Bearer "}

credential_routes: Normalised routing table. Each row maps a (host, path_prefix)
                   pattern to a credential. The broker looks up by host (index),
                   then picks the best matching path_prefix in Python.
                   Replaces the earlier routes JSON column approach entirely.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-09
"""

import json
import os
from typing import Optional

from alembic import op
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


# ── Helpers (self-contained — migration must not import from src/) ────────────

def _load_spec(spec_path: str) -> Optional[dict]:
    if not spec_path or not os.path.exists(spec_path):
        return None
    try:
        with open(spec_path) as f:
            content = f.read()
        if spec_path.endswith((".yaml", ".yml")):
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                pass
        return json.loads(content)
    except Exception:
        return None


def _deep_merge(base: dict, overlay: dict) -> dict:
    import copy
    result = copy.deepcopy(base)
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


def _load_api_desc(conn, api_id: str) -> dict:
    row = conn.execute(
        text("SELECT spec_path FROM apis WHERE id = :api_id"), {"api_id": api_id}
    ).fetchone()
    spec_path = row[0] if row else None
    doc = _load_spec(spec_path) if spec_path else {}
    if doc is None:
        doc = {}
    overlay_rows = conn.execute(
        text(
            "SELECT overlay FROM api_overlays WHERE api_id = :api_id "
            "AND status IN ('confirmed', 'pending') ORDER BY created_at ASC"
        ),
        {"api_id": api_id},
    ).fetchall()
    for (overlay_json,) in overlay_rows:
        try:
            overlay = json.loads(overlay_json)
            for action in overlay.get("actions", []):
                if action.get("target") == "$" and isinstance(action.get("update"), dict):
                    doc = _deep_merge(doc, action["update"])
        except Exception:
            pass
    return doc


def _get_security_schemes(spec: Optional[dict]) -> dict:
    if not spec:
        return {}
    schemes = spec.get("components", {}).get("securitySchemes", {})
    if schemes:
        return schemes
    return spec.get("securityDefinitions", {})


def _infer_auth_type_from_spec(spec: Optional[dict]) -> Optional[str]:
    schemes = _get_security_schemes(spec)
    if not schemes:
        return None
    if any(v.get("type") == "http" and v.get("scheme", "").lower() == "basic"
           for v in schemes.values()):
        return "basic"
    if any(v.get("type") == "http" and v.get("scheme", "").lower() not in ("basic", "digest")
           for v in schemes.values()):
        return "bearer"
    if any(v.get("type") == "apiKey" for v in schemes.values()):
        return "apiKey"
    return None


_IDENTITY_KEYWORDS = ("email", "user", "username", "login", "account", "identity")
_SECRET_PREFERENCE = ("token", "key", "secret", "api")


def _apikey_scheme_from_spec(spec: dict, identity: Optional[str]) -> Optional[dict]:
    raw_schemes = _get_security_schemes(spec)

    if not identity:
        http_bearer = next(
            (v for v in raw_schemes.values()
             if v.get("type") == "http" and v.get("scheme", "").lower() == "bearer"),
            None,
        )
        if http_bearer:
            return {"in": "header", "name": "Authorization", "prefix": "Bearer "}

    apikey_schemes = {
        k: v for k, v in raw_schemes.items()
        if v.get("type") == "apiKey" and v.get("in") == "header" and v.get("name")
    }
    if not apikey_schemes:
        return None

    def _is_identity_slot(header_name: str) -> bool:
        return any(kw in header_name.lower() for kw in _IDENTITY_KEYWORDS)

    def _secret_score(header_name: str) -> int:
        h = header_name.lower()
        for i, kw in enumerate(_SECRET_PREFERENCE):
            if kw in h:
                return i
        return len(_SECRET_PREFERENCE)

    if identity:
        if len(apikey_schemes) == 1:
            s = next(iter(apikey_schemes.values()))
            return {"in": "header", "name": s["name"]}
        identity_candidates = {k: v for k, v in apikey_schemes.items()
                                if _is_identity_slot(v["name"])}
        secret_candidates   = {k: v for k, v in apikey_schemes.items()
                                if not _is_identity_slot(v["name"])}
        if identity_candidates and secret_candidates:
            secret_s   = min(secret_candidates.values(), key=lambda v: _secret_score(v["name"]))
            identity_s = next(iter(identity_candidates.values()))
            return {
                "secret":   {"in": "header", "name": secret_s["name"]},
                "identity": {"in": "header", "name": identity_s["name"]},
            }
        s = next(iter(apikey_schemes.values()))
        return {"in": "header", "name": s["name"]}
    else:
        if len(apikey_schemes) == 1:
            s = next(iter(apikey_schemes.values()))
            return {"in": "header", "name": s["name"]}
        best = min(apikey_schemes.values(), key=lambda v: _secret_score(v["name"]))
        return {"in": "header", "name": best["name"]}


def _parse_route(route: str) -> tuple[str, str]:
    """Split a route string into (host, path_prefix).

    Examples:
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


# ── Migration ─────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # 1. server_variables column (defensive — may already exist if migrating from pre-squash branch)
    try:
        op.execute(
            "ALTER TABLE credentials ADD COLUMN server_variables TEXT DEFAULT NULL"
        )
    except Exception:
        pass  # column already exists

    # 2. scheme column (defensive)
    try:
        op.execute(
            "ALTER TABLE credentials ADD COLUMN scheme TEXT DEFAULT NULL"
        )
    except Exception:
        pass  # column already exists

    # 3. credential_routes table
    op.execute("""
        CREATE TABLE IF NOT EXISTS credential_routes (
            credential_id  TEXT NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
            host           TEXT NOT NULL,
            path_prefix    TEXT NOT NULL DEFAULT '/',
            PRIMARY KEY (credential_id, host, path_prefix)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_credential_routes_host "
        "ON credential_routes(host)"
    )

    # 4. Backfill scheme on existing credentials
    rows = conn.execute(
        text("SELECT id, auth_type, api_id, identity FROM credentials WHERE scheme IS NULL")
    ).fetchall()

    BEARER_SCHEME = json.dumps({"in": "header", "name": "Authorization", "prefix": "Bearer "})
    BASIC_SCHEME  = json.dumps({"in": "header", "name": "Authorization", "prefix": "Basic ",
                                "encode": "base64"})

    for cred_id, auth_type_raw, api_id, identity in rows:
        auth_type = auth_type_raw
        doc = None
        if api_id:
            doc = _load_api_desc(conn, api_id)
        if not auth_type:
            auth_type = _infer_auth_type_from_spec(doc)

        scheme_json: Optional[str] = None
        if auth_type in ("bearer", "oauth2"):
            scheme_json = BEARER_SCHEME
        elif auth_type == "basic":
            scheme_json = BASIC_SCHEME
        elif auth_type == "apiKey" and doc:
            extracted = _apikey_scheme_from_spec(doc, identity)
            if extracted:
                scheme_json = json.dumps(extracted)
        elif auth_type == "pipedream_oauth":
            continue

        if scheme_json is not None:
            conn.execute(
                text("UPDATE credentials SET scheme = :scheme WHERE id = :cred_id"),
                {"scheme": scheme_json, "cred_id": cred_id},
            )

    # 5. Backfill credential_routes from server_variables (preferred), API spec base URL, or api_id
    cred_rows = conn.execute(
        text("SELECT id, api_id, server_variables FROM credentials")
    ).fetchall()

    for cred_id, api_id, sv_json in cred_rows:
        route_host_raw = None

        # 1. Try server_variables: pick first value that looks like a hostname
        if sv_json:
            try:
                sv = json.loads(sv_json)
                for v in sv.values():
                    if isinstance(v, str) and ('.' in v or ':' in v):
                        route_host_raw = v
                        break
            except Exception:
                pass

        # 2. Try API spec base URL as a full route (resolves overlays like portainer)
        if not route_host_raw and api_id:
            try:
                doc = _load_api_desc(conn, api_id)
                servers = (doc.get("servers") or
                           ([{"url": f"https://{doc['host']}"}] if doc.get("host") else []))
                if servers:
                    base_url = servers[0].get("url", "")
                    # Substitute any server template variables from credential sv
                    if sv_json and '{' in base_url:
                        try:
                            sv = json.loads(sv_json)
                            import re as _re
                            for var in _re.findall(r'\{([^}]+)\}', base_url):
                                if var in sv:
                                    base_url = base_url.replace(f'{{{var}}}', sv[var])
                        except Exception:
                            pass
                    # Only use if fully resolved and not a generic example host
                    if base_url and '{' not in base_url and 'example.com' not in base_url:
                        route_host_raw = base_url  # full URL, _parse_route will strip scheme
            except Exception:
                pass

        # 3. Fall back to api_id
        if not route_host_raw:
            if not api_id:
                continue
            route_host_raw = api_id

        host, path_prefix = _parse_route(route_host_raw)
        conn.execute(
            text(
                "INSERT OR IGNORE INTO credential_routes "
                "(credential_id, host, path_prefix) VALUES (:cid, :host, :pp)"
            ),
            {"cid": cred_id, "host": host, "pp": path_prefix},
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS credential_routes")
    # Rebuild credentials without server_variables and scheme (SQLite <3.35 workaround)
    op.execute("""
        CREATE TABLE credentials_new (
            id              TEXT PRIMARY KEY,
            label           TEXT NOT NULL,
            env_var         TEXT UNIQUE,
            encrypted_value TEXT NOT NULL,
            created_at      REAL DEFAULT (unixepoch()),
            updated_at      REAL,
            api_id          TEXT,
            auth_type       TEXT,
            source          TEXT,
            identity        TEXT,
            scheme_name     TEXT
        )
    """)
    op.execute("""
        INSERT INTO credentials_new
            SELECT id, label, env_var, encrypted_value, created_at, updated_at,
                   api_id, auth_type, source, identity, scheme_name
            FROM credentials
    """)
    op.execute("DROP TABLE credentials")
    op.execute("ALTER TABLE credentials_new RENAME TO credentials")
