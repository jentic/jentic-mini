"""
Jentic Mini — main.py
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from src.auth import APIKeyMiddleware
from src.negotiate import negotiate_middleware
from src.db import init_db, setup_state
from src.routers import apis as apis_router
from src.routers import search as search_router
from src.routers import credentials as creds_router
from src.routers import debug as debug_router
from src.routers import toolkits as toolkits_router
from src.routers.toolkits import policy_router as toolkits_policy_router
from src.routers import access_requests as access_requests_router
from src.routers import notes as notes_router
from src.routers import capability as capability_router
from src.routers import workflows as workflows_router
from src.routers import import_ as import_router
from src.routers import catalog as catalog_router
from src.routers import traces as traces_router
from src.routers import broker as broker_router
from src.routers import overlays as overlays_router
from src.routers import jobs as jobs_router
from src.routers import user as user_router
from src.routers import default_key as default_key_router
from src.routers import oauth_brokers as oauth_brokers_router
from src.routers.apis import rebuild_index_on_startup
from src.routers.catalog import refresh_catalog_if_stale
from src.startup import self_register, seed_broker_apps
from src.utils import build_absolute_url

APP_VERSION = os.getenv("APP_VERSION", "0.2.0")

logging.basicConfig(level=(os.getenv("LOG_LEVEL") or "info").upper())
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
log = logging.getLogger("jentic")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Jentic starting — initialising DB")
    await init_db()
    log.info("Jentic building BM25 index")
    await rebuild_index_on_startup()
    log.info("Jentic self-registering")
    await self_register(app)
    log.info("Jentic refreshing catalog manifest")
    await refresh_catalog_if_stale()
    log.info("Jentic seeding broker app mappings")
    await seed_broker_apps()
    log.info("Jentic loading OAuth brokers")
    from src.brokers.pipedream import PipedreamOAuthBroker
    from src.oauth_broker import registry as oauth_broker_registry
    _pd_brokers = await PipedreamOAuthBroker.from_db()
    for _b in _pd_brokers:
        oauth_broker_registry.register(_b)
    log.info("Jentic loaded %d OAuth broker(s)", len(_pd_brokers))
    log.info("Jentic ready")
    yield
    log.info("Jentic shutting down")


# Tag order controls Swagger UI section order.
# Within each section, operations appear in router-registration order.
_TAGS_METADATA = [
    {
        "name": "search",
        "description": "**Start here.** Full-text and semantic search across all registered APIs and operations.",
    },
    {
        "name": "inspect",
        "description": "Inspect capability details, list APIs and operations.",
    },
    {
        "name": "execute",
        "description": (
            "Transparent request broker — runs API operations and Arazzo workflows. "
            "Prefix any registered host to route through the broker: "
            "`POST /api.stripe.com/v1/payment_intents`. "
            "Credential injection, policy enforcement, and simulate mode built-in."
        ),
    },
    {
        "name": "observe",
        "description": "Read async job handles and execution traces.",
    },
    {
        "name": "toolkits",
        "description": "Manage toolkits: scoped credential bundles with access keys, permissions, and access requests.",
    },
    {
        "name": "credentials",
        "description": "Manage upstream API credentials in the vault (humans/admin only). Values are write-only — never returned after creation.",
    },
    {
        "name": "user",
        "description": "Human account management: create account, login, logout, and agent key generation.",
    },
    {
        "name": "catalog",
        "description": "Register APIs, upload specs, manage overlays and notes.",
    },
]

app = FastAPI(
    title="Jentic Mini",
    openapi_tags=_TAGS_METADATA,
    description=(
        "**Jentic Mini** is the open-source, self-hosted implementation of the Jentic API — "
        "fully API-compatible with the [Jentic hosted and VPC editions](https://jentic.com).\n\n"
        "## What is Jentic Mini?\n"
        "Jentic Mini gives any agent a local execution layer: search a catalog of registered APIs, "
        "broker authenticated requests without exposing credentials to the agent, enforce access "
        "policies, and observe every execution. It is designed to be dropped in as a self-hosted "
        "alternative to the Jentic cloud service.\n\n"
        "## Hosted vs Self-hosted\n"
        "The **Jentic hosted and VPC editions** offer deeper implementations across three areas:\n\n"
        "| Capability | Jentic Mini (this) | Jentic hosted / VPC |\n"
        "|------------|-------------------|---------------------|\n"
        "| **Search** | BM25 full-text search | Advanced semantic search (~64% accuracy improvement over BM25) |\n"
        "| **Request brokering** | In-process credential injection | Scalable AWS Lambda-based broker with encryption at rest and in-transit, SOC 2-grade security, and 3rd-party credential vault integrations (HashiCorp Vault, AWS Secrets Manager, etc.) |\n"
        "| **Simulation** | Basic simulate mode | Full sandbox for simulating API calls and toolkit behaviour (enterprise-only) |\n"
        "| **Catalog** | Local registry only | Central catalog — aggregates the collective know-how of agents across API definitions and Arazzo workflows |\n\n"
        "## Authentication\n"
        "**Agents** — provide `X-Jentic-API-Key: tk_xxx` header.\n"
        "**Humans** — [log in here](/login) for a session cookie (required for admin operations).\n"
        "First time? Call `POST /default-api-key/generate` from a trusted subnet to get your agent key.\n\n"
        "## Tag groups\n"
        "| Tag | Who uses it | Purpose |\n"
        "|-----|-------------|----------|\n"
        "| **search** | Agents | Full-text search — the main entrypoint |\n"
        "| **inspect** | Agents | Inspect capabilities, list APIs and operations |\n"
        "| **execute** | Agents | Transparent request broker — runs API operations and Arazzo workflows. "
        "Credential injection, policy enforcement, and simulate mode built-in. |\n"
        "| **toolkits** | Agents/Humans | Toolkits, access keys, permissions, access requests |\n"
        "| **observe** | Agents | Read execution traces |\n"
        "| **catalog** | Humans/admin | Register APIs, upload specs, overlays, notes |\n"
        "| **credentials** | Humans only | Manage the credentials vault |\n\n"
        "Agents with a toolkit key need: **search**, **inspect**, **execute**, **toolkits** (read), **observe**."
    ),    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    debug=False,
)

app.add_middleware(APIKeyMiddleware)
app.middleware("http")(negotiate_middleware)

# ── Static dir — defined early so route handlers can reference it ──────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.include_router(capability_router.router, tags=["inspect"])
app.include_router(workflows_router.router)
app.include_router(import_router.router, tags=["catalog"])
app.include_router(catalog_router.router, tags=["catalog"])
app.include_router(jobs_router.router)
app.include_router(traces_router.router, tags=["observe"])
app.include_router(overlays_router.router, tags=["catalog"])  # must be before apis (path converter conflict)
app.include_router(apis_router.router, tags=["catalog"])
app.include_router(search_router.router, tags=["search"])
app.include_router(creds_router.router, tags=["credentials"])
app.include_router(toolkits_router.router, tags=["toolkits"])
app.include_router(toolkits_policy_router, prefix="/toolkits", tags=["toolkits"])
app.include_router(access_requests_router.router, prefix="/toolkits", tags=["toolkits"])
app.include_router(notes_router.router, tags=["catalog"])
app.include_router(debug_router.router, include_in_schema=False)
app.include_router(user_router.router)
app.include_router(default_key_router.router)
app.include_router(oauth_brokers_router.router, tags=["credentials"])

# ── Meta routes: health + root — MUST be before broker catch-all ─────────────
@app.get("/health", tags=["meta"])
async def health(request: Request):
    """Returns current setup state with explicit instructions for agents."""
    state = await setup_state()

    if not state["default_key_claimed"]:
        return {
            "status": "setup_required",
            "account_created": state["account_created"],
            "message": "No default API key has been issued yet.",
            "next_step": "Call POST /default-api-key/generate from a trusted subnet to obtain your agent key.",
            "generate_url": "/default-api-key/generate",
            "version": APP_VERSION,
        }

    if not state["account_created"]:
        return {
            "status": "account_required",
            "message": "Agent key is active. No admin account has been created yet.",
            "next_step": "Tell your user to visit setup_url to create their admin account. "
                         "Your agent key works immediately — you do not need to wait.",
            "setup_url": build_absolute_url(request, "/user/create"),
            "version": APP_VERSION,
        }

    # Fully set up
    async with __import__("aiosqlite").connect(__import__("src.db", fromlist=["DB_PATH"]).DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM apis") as cur:
            (api_count,) = await cur.fetchone()

    return {
        "status": "ok",
        "version": APP_VERSION,
        "apis_registered": api_count,
    }


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
async def favicon():
    path = STATIC_DIR / "favicon.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    return FileResponse(path, media_type="image/png")


@app.get("/login", include_in_schema=False)
async def login_page(error: str | None = None):
    """Human-friendly login form — POSTs to /user/login?redirect_to=/docs."""
    from fastapi.responses import HTMLResponse
    err_html = f'<p class="error">{error}</p>' if error else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jentic Mini — Log In</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
    .card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 12px; padding: 2.5rem; width: 100%; max-width: 380px; }}
    h1 {{ font-size: 1.4rem; color: #a5b4fc; margin-bottom: 0.25rem; }}
    .sub {{ font-size: 0.85rem; color: #888; margin-bottom: 1.75rem; }}
    label {{ display: block; font-size: 0.8rem; color: #aaa; margin-bottom: 0.35rem; margin-top: 1rem; }}
    input {{ width: 100%; padding: 0.6rem 0.8rem; background: #0f3460; border: 1px solid #334; border-radius: 6px;
             color: #e0e0e0; font-size: 0.95rem; outline: none; }}
    input:focus {{ border-color: #a5b4fc; }}
    button {{ margin-top: 1.5rem; width: 100%; padding: 0.7rem; background: #6366f1; border: none; border-radius: 6px;
              color: #fff; font-size: 1rem; cursor: pointer; font-weight: 600; }}
    button:hover {{ background: #818cf8; }}
    .error {{ color: #f87171; font-size: 0.85rem; margin-top: 1rem; text-align: center; }}
    .back {{ text-align: center; margin-top: 1rem; font-size: 0.8rem; }}
    .back a {{ color: #a5b4fc; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Jentic Mini</h1>
    <p class="sub">Admin login</p>
    <form method="POST" action="/user/login?redirect_to=/docs">
      <label for="username">Username</label>
      <input id="username" name="username" type="text" autocomplete="username" required autofocus>
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
      {err_html}
      <button type="submit">Log in →</button>
    </form>
    <p class="back"><a href="/docs">← Back to API docs</a></p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/", tags=["meta"], include_in_schema=False)
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Jentic API is running. See /docs for API documentation."}


# ── Docs served locally (no CDN, works offline / on patchy connections) ───────
@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    # Custom Swagger UI with persistAuthorization + auth banner
    html = """<!DOCTYPE html>
<html>
<head>
  <title>Jentic — Swagger UI</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" type="text/css" href="/static/swagger-ui.css" >
  <style>
    .auth-banner {
      background: #1a1a2e; border-left: 4px solid #667eea;
      color: #e0e0e0; padding: 12px 20px; font-family: monospace;
      font-size: 14px; margin: 0;
    }
    .auth-banner strong { color: #667eea; }
    .auth-banner code { background: #2d2d2d; padding: 2px 6px; border-radius: 3px; }
  </style>
</head>
<body>
<div class="auth-banner">
  🔑 <strong>Authentication.</strong>
  <strong>Agents:</strong> Click <strong>Authorize 🔓</strong> and enter your <code>tk_xxx</code> key in the <em>JenticApiKey</em> field.
  <strong>Humans:</strong> Click <strong>Authorize 🔓</strong> and use the <em>HumanLogin</em> username + password form — or <a href="/login" style="color:#a5b4fc">log in here</a> for a persistent browser session.
  First time? Call <code>POST /default-api-key/generate</code> from a local subnet.
</div>
<div id="swagger-ui"></div>
<script src="/static/swagger-ui-bundle.js"> </script>
<script>
  window.onload = function() {
    SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: '#swagger-ui',
      presets: [ SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset ],
      layout: "BaseLayout",
      persistAuthorization: true,
      tryItOutEnabled: true,
      requestInterceptor: function(req) { return req; },
    })
  }
</script>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/redoc", include_in_schema=False)
async def redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Jentic — Redoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


# ── Broker catch-all — MUST be registered last ────────────────────────────────
# Paths whose first segment contains "." route to the broker.
# All Jentic-internal routes above take priority by registration order.
# ── Static files — MUST be before broker catch-all ────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    # Also serve Vite build assets at /assets (Vite default output path)
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# ── SPA middleware — serve index.html for browser navigations to SPA routes ───
# API clients (Accept: application/json) get the API response.
# Browsers (Accept: text/html) get the React SPA.
_SPA_PATHS = {
    "/approve", "/search", "/catalog", "/workflows", "/toolkits",
    "/credentials", "/traces", "/jobs", "/oauth-brokers", "/setup",
}

@app.middleware("http")
async def spa_middleware(request: Request, call_next):
    if request.method == "GET":
        path = request.url.path
        accept = request.headers.get("accept", "")
        wants_html = any(part.strip().startswith("text/html") for part in accept.split(","))
        if wants_html and any(path == p or path.startswith(p + "/") for p in _SPA_PATHS):
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return Response(content="UI not built", status_code=404, media_type="text/plain")
    return await call_next(request)

# ── Broker catch-all — MUST be registered last ────────────────────────────────
app.include_router(broker_router.router)


# ── Custom OpenAPI schema with API key security scheme ────────────────────────

# Paths that are open (no tk_xxx key required) — shown as unlocked in Swagger UI.
# Broker paths (/{host}/...) are open passthrough but handled dynamically by the
# broker router and don't appear as static paths in the schema.
_OPEN_OPERATIONS: set[tuple[str, str]] = {
    # path, method
    ("/health", "get"),
    ("/user/create", "post"),
    ("/user/login", "post"),
    ("/user/token", "post"),
    ("/default-api-key/generate", "post"),
    # Search + inspect: public read-only discovery
    ("/search", "get"),
    ("/apis", "get"),
    ("/apis/{api_id}", "get"),
    ("/apis/{api_id}/overlays", "get"),
    ("/apis/{api_id}/overlays/{overlay_id}", "get"),
    # Workflow execution is open passthrough (upstream auth is upstream's problem)
    ("/workflows", "get"),
    ("/workflows/{slug}", "get"),
    ("/workflows/{slug}", "post"),
}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,  # controls section order in Swagger UI
    )
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "JenticApiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Jentic-API-Key",
            "description": "Agent toolkit key (`tk_xxx`). Issue via `POST /default-api-key/generate`.",
        },
        "HumanLogin": {
            "type": "oauth2",
            "description": "Human admin session. Fill in username + password to get a Bearer JWT.",
            "flows": {
                "password": {
                    "tokenUrl": "/user/token",
                    "scopes": {},
                }
            },
        },
    }
    # Global default: endpoints require JenticApiKey OR HumanLogin
    schema["security"] = [{"JenticApiKey": []}, {"HumanLogin": []}]

    # Override: mark open/public operations as unlocked (security: [])
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            if (path, method.lower()) in _OPEN_OPERATIONS:
                operation["security"] = []

    # Reorder paths: group by root resource prefix, then depth (least → most specific),
    # then alphabetically within the same depth. This produces the natural logical order:
    #   /apis → /apis/{id} → /apis/{id}/openapi.json → /apis/{id}/operations → …
    # Routing requires specific-suffix routes registered before catch-alls, but docs
    # should read from least specific to most specific.
    def _path_sort_key(p: str) -> tuple:
        parts = [s for s in p.split("/") if s]
        root = parts[0] if parts else ""
        depth = len(parts)
        return (root, depth, p)

    schema["paths"] = dict(
        sorted(schema.get("paths", {}).items(), key=lambda kv: _path_sort_key(kv[0]))
    )

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
