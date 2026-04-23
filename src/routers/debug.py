"""Debug endpoints — hidden from public docs (include_in_schema=False on all routes)."""

import asyncio
import inspect
import json
import logging
import os
import sys
import uuid
from pathlib import Path

from arazzo_runner import ArazzoRunner
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Request

import src.vault as vault
from src.auth import client_ip, default_allowed_ips, is_trusted_ip, trusted_subnets
from src.config import DATA_DIR
from src.db import DEFAULT_TOOLKIT_ID, get_db
from src.routers.apis import rebuild_index
from src.routers.workflows import execute_workflow_core, parse_arazzo


log = logging.getLogger("jentic")
router = APIRouter(prefix="/debug", tags=["debug"], include_in_schema=False)


@router.get("/whoami")
async def whoami(request: Request):
    """Return IP detection diagnostics — use to verify source IP is not masked by Docker/NPM."""
    raw_client = request.client.host if request.client else None
    xff = request.headers.get("x-forwarded-for", None)
    x_real_ip = request.headers.get("x-real-ip", None)
    resolved_ip = client_ip(request)
    return {
        "resolved_ip": resolved_ip,
        "is_trusted": is_trusted_ip(resolved_ip),
        "trusted_subnets": trusted_subnets(),
        "default_allowed_ips": default_allowed_ips(),
        "raw": {
            "request.client.host": raw_client,
            "x-forwarded-for": xff,
            "x-real-ip": x_real_ip,
        },
        "all_headers": dict(request.headers),
    }


@router.get("/auth-internals")
async def auth_internals():
    result = {}
    # arazzo_runner private submodule paths — kept local so this endpoint still
    # returns a useful error JSON if upstream restructures internal modules.
    try:
        from arazzo_runner.auth.credentials.models import (  # noqa: PLC0415
            AuthValue,
            Credential,
            RequestAuthValue,
            SecurityScheme,
        )

        result["Credential"] = inspect.getsource(Credential)[:2500]
        result["SecurityScheme"] = inspect.getsource(SecurityScheme)[:1500]
        result["AuthValue"] = inspect.getsource(AuthValue)[:1000]
        result["RequestAuthValue"] = inspect.getsource(RequestAuthValue)[:1000]
    except Exception as e:
        result["models_err"] = str(e)

    try:
        from arazzo_runner.auth.credentials.fetch import FetchStrategy  # noqa: PLC0415

        result["FetchStrategy_src"] = inspect.getsource(FetchStrategy)[:3000]
    except Exception as e:
        result["fetch_err"] = str(e)

    try:
        from arazzo_runner.auth.credentials import provider as prov_mod  # noqa: PLC0415

        result["provider_dir"] = [x for x in dir(prov_mod) if not x.startswith("_")]
        # Get all classes in provider module
        for name in dir(prov_mod):
            obj = getattr(prov_mod, name)
            if inspect.isclass(obj) and obj.__module__.startswith("arazzo_runner"):
                try:
                    result[f"class_{name}"] = inspect.getsource(obj)[:1500]
                except Exception:
                    pass
    except Exception as e:
        result["provider_err"] = str(e)

    return result


@router.get("/env-mappings")
async def env_mappings(arazzo_path: str = ""):
    try:
        runner = ArazzoRunner.from_arazzo_path(arazzo_path)
        mappings = runner.get_env_mappings()
        return {"mappings": mappings}
    except Exception:
        log.exception("env-mappings failed for %s", arazzo_path)
        return {"error": "Failed to load env mappings. Check server logs for details."}


@router.get("/spec")
async def spec_info(path: str = ""):
    if not path:
        return {"error": "path is required", "exists": False}
    data_root = DATA_DIR.resolve()
    p = (data_root / path).resolve()
    # Restrict to the data directory to prevent path traversal
    try:
        p.relative_to(data_root)
    except ValueError:
        return {"error": "path must be inside the data directory", "exists": False}
    if not p.exists():
        return {"exists": False, "path": path}
    if not p.is_file():
        return {"error": "path must point to a regular file", "exists": True}
    if p.suffix.lower() != ".json":
        return {"error": "only .json files are supported", "exists": True}
    try:
        raw_text = p.read_text()
    except UnicodeDecodeError:
        return {"error": "file is not valid UTF-8 text", "exists": True}
    try:
        doc = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"error": "file does not contain valid JSON", "exists": True}
    paths = doc.get("paths", {})
    sample = []
    for api_path, methods in list(paths.items())[:5]:
        for method, op in methods.items():
            if method.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                sample.append(f"{method.upper()} {api_path}: {op.get('operationId', '')}")
                break
    return {
        "exists": True,
        "size_kb": p.stat().st_size // 1024,
        "paths_count": len(paths),
        "sample": sample,
        "security_schemes": doc.get("components", {}).get("securitySchemes", {}),
        "global_security": doc.get("security", []),
    }


@router.post("/admin/purge-old-api-ids", status_code=200)
async def purge_old_api_ids():
    """
    One-time migration helper: delete all API records whose IDs are old-style
    hand-crafted slugs (no dot in them, or degenerate derived IDs like 'com').

    Keeps only IDs that look like URL-derived ones (contain a dot, not a TLD stub,
    don't start with '{').
    """

    def is_derived(id_: str) -> bool:
        return "." in id_ and not id_.startswith("{") and id_ not in ("com", "net", "org")

    async with get_db() as db:
        async with db.execute("SELECT id FROM apis") as cur:
            all_ids = [r[0] for r in await cur.fetchall()]

        old_ids = [id_ for id_ in all_ids if not is_derived(id_)]

        for id_ in old_ids:
            await db.execute("DELETE FROM operations WHERE api_id=?", (id_,))
            await db.execute("DELETE FROM apis WHERE id=?", (id_,))
        await db.commit()

    # Single rebuild after all deletes
    await rebuild_index()

    remaining = []
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis ORDER BY id") as cur:
            remaining = [r[0] for r in await cur.fetchall()]

    return {"deleted": old_ids, "remaining": remaining}


@router.get("/vault-status")
async def vault_status():
    """Diagnose vault key source and test round-trip encrypt/decrypt."""
    db_path = os.getenv("DB_PATH", "/app/data/jentic-mini.db")
    key_file = Path(db_path).parent / "vault.key"
    env_key = os.getenv("JENTIC_VAULT_KEY", "")

    result = {
        "env_var_set": bool(env_key),
        "env_var_prefix": env_key[:6] + "..." if env_key else None,
        "key_file_exists": key_file.exists(),
        "key_file_path": str(key_file),
        "key_file_prefix": None,
        "active_source": None,
        "round_trip_ok": False,
        "round_trip_error": None,
    }

    # Determine active key
    active_key = None
    if env_key:
        try:
            Fernet(env_key.encode())
            active_key = env_key
            result["active_source"] = "env_var"
        except Exception as e:
            result["env_var_error"] = str(e)

    if active_key is None and key_file.exists():
        file_key = key_file.read_text().strip()
        result["key_file_prefix"] = file_key[:6] + "..."
        try:
            Fernet(file_key.encode())
            active_key = file_key
            result["active_source"] = "vault.key_file"
        except Exception as e:
            result["key_file_error"] = str(e)

    if active_key is None:
        result["active_source"] = "none_valid"
        return result

    # Round-trip test
    try:
        f = Fernet(active_key.encode())
        token = f.encrypt(b"test-value")
        decrypted = f.decrypt(token)
        result["round_trip_ok"] = decrypted == b"test-value"
    except Exception as e:
        result["round_trip_error"] = str(e)

    # Test decrypting all credentials (without returning values)
    cred_results = []
    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT id, encrypted_value FROM credentials ORDER BY created_at"
            ) as cur:
                rows = await cur.fetchall()
        f = Fernet(active_key.encode())
        for cred_id, enc_val in rows:
            try:
                decrypted = f.decrypt(enc_val.encode())
                cred_results.append({"id": cred_id, "ok": True})
            except InvalidToken:
                cred_results.append({"id": cred_id, "ok": False, "error": "key_mismatch"})
            except Exception as e:
                cred_results.append({"id": cred_id, "ok": False, "error": str(e)})
    except Exception as e:
        cred_results.append({"error": str(e)})
    result["credentials"] = cred_results

    return result


@router.get("/pycheck")
async def pycheck():
    """Check Python package availability."""
    results = {}
    for pkg in ["httpx", "cryptography", "rank_bm25", "fastapi"]:
        try:
            mod = __import__(pkg)
            results[pkg] = getattr(mod, "__version__", "installed")
        except ImportError:
            results[pkg] = "MISSING"
    return results


@router.get("/broker-cred-test")
async def broker_cred_test(host: str = "api.elevenlabs.io"):
    """Test broker credential lookup for a given host."""
    # Step 1: find API
    async with get_db() as db:
        async with db.execute(
            "SELECT id, spec_path FROM apis WHERE id=? OR id LIKE ?",
            (host, f"{host}%"),
        ) as cur:
            api_row = await cur.fetchone()

    if not api_row:
        return {"error": "API not found", "host": host}

    api_id, spec_path = api_row
    env_vars = await vault.get_all_env_vars()

    # Step 2: try arazzo-runner
    try:
        runner = ArazzoRunner.from_openapi_path(spec_path)
        mappings = runner.get_env_mappings()
        auth_mappings = mappings.get("auth", {})
    except Exception:
        log.exception("arazzo-runner failed for %s", spec_path)
        return {"error": "arazzo-runner failed. Check server logs for details."}

    # Step 3: resolve headers
    with open(spec_path) as f:
        spec = json.load(f)
    security_schemes = spec.get("components", {}).get("securitySchemes", {})
    global_security = spec.get("security", [])

    result = {
        "api_id": api_id,
        "spec_path": spec_path,
        "arazzo_mappings": auth_mappings,
        "vault_env_vars": list(env_vars.keys()),
        "global_security": global_security,
        "injected_headers": {},
    }

    for sec_req in global_security:
        for scheme_name in sec_req:
            scheme = security_schemes.get(scheme_name, {})
            mapping = auth_mappings.get(scheme_name, {})
            env_var_name = mapping.get("token") or mapping.get("key")
            value = env_vars.get(env_var_name) if env_var_name else None
            result["injected_headers"][scheme_name] = {
                "env_var": env_var_name,
                "found": value is not None,
                "scheme_type": scheme.get("type"),
            }

    return result


@router.post("/admin/fix-credentials", include_in_schema=False)
async def fix_credentials():
    """One-off: backfill api_id/scheme_name on pre-overlay credentials and enroll in default."""
    async with get_db() as db:
        await db.execute(
            "UPDATE credentials SET api_id='techpreneurs.ie', scheme_name='DiscourseApiKey' WHERE env_var='DISCOURSE_API_KEY'"
        )
        await db.execute(
            "UPDATE credentials SET api_id='techpreneurs.ie', scheme_name='DiscourseUsername' WHERE env_var='DISCOURSE_API_USERNAME'"
        )
        for ev in ("DISCOURSE_API_KEY", "DISCOURSE_API_USERNAME", "DISCOURSE_USERNAME"):
            async with db.execute("SELECT id FROM credentials WHERE env_var=?", (ev,)) as cur:
                row = await cur.fetchone()
            if row:
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (id, toolkit_id, credential_id) VALUES (?,?,?)",
                    (str(uuid.uuid4()), DEFAULT_TOOLKIT_ID, row[0]),
                )
        await db.commit()
        async with db.execute(
            "SELECT env_var, api_id, scheme_name FROM credentials WHERE api_id IS NOT NULL"
        ) as cur:
            updated = await cur.fetchall()
    return {"updated": updated}


@router.get("/admin/check-creds", include_in_schema=False)
async def check_creds():
    async with get_db() as db:
        async with db.execute("SELECT id, env_var, api_id, scheme_name FROM credentials") as cur:
            creds = await cur.fetchall()
        async with db.execute(
            "SELECT toolkit_id, credential_id FROM toolkit_credentials WHERE toolkit_id=?",
            (DEFAULT_TOOLKIT_ID,),
        ) as cur:
            cc = await cur.fetchall()
        async with db.execute("SELECT id FROM toolkits WHERE id=?", (DEFAULT_TOOLKIT_ID,)) as cur:
            coll = await cur.fetchone()
    return {"credentials": creds, "toolkit_credentials": cc, "default_toolkit_exists": bool(coll)}


@router.get("/async-subprocess-test", include_in_schema=False)
async def async_subprocess_test():
    """Test if subprocesses work correctly from both sync and background task contexts."""
    script = """
import socket, sys, json

results = {}
try:
    addr = socket.getaddrinfo("localhost", 8900)
    results["localhost_dns"] = "ok"
except Exception as e:
    results["localhost_dns"] = f"ERROR: {e}"

try:
    addr = socket.getaddrinfo("techpreneurs.ie", 443)
    results["techpreneurs_dns"] = "ok"
except Exception as e:
    results["techpreneurs_dns"] = f"ERROR: {e}"

try:
    import urllib.request
    r = urllib.request.urlopen("http://localhost:8900/health", timeout=5)
    results["localhost_http"] = r.read(50).decode()
except Exception as e:
    results["localhost_http"] = f"ERROR: {e}"

print(json.dumps(results))
"""

    async def run_it():
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        return {"stdout": out.decode().strip(), "stderr": err.decode().strip()[:300]}

    # Direct call
    direct = await run_it()

    # Background task
    bg_result = {}

    async def bg():
        r = await run_it()
        bg_result.update(r)

    task = asyncio.create_task(bg())
    await task

    return {"direct": direct, "background": bg_result}


@router.post("/test-async-workflow", include_in_schema=False)
async def test_async_workflow():
    """Run dispatch_workflow with Prefer: wait=0 and capture full exception details."""
    error_detail = {}

    async def instrumented_bg():
        try:
            # Get the workflow
            async with get_db() as db:
                async with db.execute(
                    "SELECT arazzo_path, name FROM workflows WHERE slug=?",
                    ("summarise-latest-topics",),
                ) as cur:
                    row = await cur.fetchone()

            if not row:
                error_detail["error"] = "workflow not found"
                return

            arazzo_path, name = row
            doc = parse_arazzo(arazzo_path)
            wf_id = doc.get("workflows", [{}])[0].get("workflowId", "summarise-latest-topics")
            error_detail["step"] = "pre-execute"

            result = await execute_workflow_core(
                slug="summarise-latest-topics",
                name=name,
                doc=doc,
                workflow_id=wf_id,
                inputs={},
                arazzo_path=arazzo_path,
                caller_api_key="",
                toolkit_id=None,
                is_simulate=False,
                trace_id=None,
            )
            error_detail["step"] = "complete"
            error_detail["status_code"] = result.status_code
        except Exception:
            log.exception("Async workflow test failed")
            error_detail["error"] = "Request failed. Check server logs."

    task = asyncio.create_task(instrumented_bg())
    await task
    return error_detail
