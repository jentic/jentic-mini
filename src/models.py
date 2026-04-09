"""
Pydantic request / response models for Jentic Mini.
Input models (Create/Patch/Register) and all response models are here.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from src.validators import NormModel, NormStr


# ── Credentials (input) ───────────────────────────────────────────────────────

class CredentialCreate(NormModel):
    label: str = Field(examples=["GitHub PAT for jentic-mini"])
    value: str = Field(examples=["ghp_1234567890abcdefghijklmnopqrstu"])
    """Plain-text secret; encrypted before storage. Always the primary credential — token, password, API key."""
    identity: str | None = Field(default=None, examples=["alice", "client_abc123"])
    """Optional identity field — username, client ID, account SID etc.
    Required for http/basic and http/digest schemes (username + password).
    For compound apiKey schemes (overlay uses canonical 'Secret'/'Identity' names), the
    Identity scheme header is injected from this field.
    Leave null for Bearer tokens, single-value API keys, and GitHub PAT-style BasicAuth."""
    api_id: str | None = Field(default=None, examples=["api.github.com"])
    """API this credential belongs to (e.g. 'techpreneurs.ie'). Required for broker injection."""
    auth_type: Literal["bearer", "basic", "apiKey"] | None = Field(
        default=None,
        examples=["bearer"],
        description=(
            "How this credential maps to the upstream API's authentication scheme. "
            "The broker uses this to find the right security scheme in the spec — "
            "it resolves by type, not by the bespoke scheme name in the overlay.\n\n"
            "| Value | Injects as | When to use |\n"
            "|---|---|---|\n"
            "| `bearer` | `Authorization: Bearer {value}` | REST APIs, OAuth access tokens, JWTs. GitHub REST API, Deepgram, Slack, etc. |\n"
            "| `basic` | `Authorization: Basic base64({identity??'token'}:{value})` | HTTP Basic auth, git-over-HTTPS. Set `identity` to the username; omit for GitHub PATs (any username accepted). |\n"
            "| `apiKey` | Custom header or query param `= {value}` | API key in a named header (X-API-Key, Api-Key, X-Auth-Key, etc.). For **compound** schemes (e.g. Discourse Api-Key + Api-Username) where the overlay uses canonical `Secret`/`Identity` scheme names, set `identity` to the username/account — a single credential covers both headers. |"
        ),
    )


class CredentialPatch(NormModel):
    label: str | None = None
    value: str | None = None
    identity: str | None = None
    """Update the identity (username / client ID) for this credential."""
    api_id: str | None = None
    auth_type: Literal["bearer", "basic", "apiKey"] | None = Field(
        default=None,
        description="Update the auth type for this credential. See `POST /credentials` for valid values and semantics.",
    )


# ── Pagination wrapper ────────────────────────────────────────────────────────

class Page(BaseModel):
    """Generic paginated envelope."""
    page: int = Field(examples=[1])
    limit: int = Field(examples=[50])
    total: int = Field(examples=[247])
    total_pages: int = Field(examples=[5])
    has_more: bool = Field(examples=[True])
    model_config = {"extra": "allow"}


# ── APIs (output) ─────────────────────────────────────────────────────────────

class ApiOut(BaseModel):
    id: str = Field(examples=["api.github.com"])
    name: str | None = Field(default=None, examples=["GitHub REST API"])
    vendor: str | None = Field(default=None, examples=["GitHub"])
    description: str | None = Field(default=None, examples=["GitHub's REST API for managing repositories, issues, and pull requests"])
    base_url: str | None = Field(default=None, examples=["https://api.github.com"])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    model_config = {"extra": "allow"}


class OperationOut(BaseModel):
    """A single API operation. id encodes method/host/path (capability ID format)."""
    id: str = Field(examples=["GET/api.github.com/repos/{owner}/{repo}/issues"])
    summary: str | None = Field(default=None, examples=["List repository issues"])
    description: str | None = Field(default=None, examples=["List issues in a repository. Only issues assigned to the authenticated user are returned."])
    model_config = {"extra": "allow"}


class ApiListPage(Page):
    """Paginated list of API providers registered in the catalog."""
    data: list[ApiOut]


class OperationListPage(Page):
    data: list[OperationOut]


# ── Search (output) ───────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    """A search result from the BM25 index — either an operation or workflow capability.

    The BM25 search index covers both API operations (parsed from OpenAPI specs) and
    workflows (parsed from Arazzo documents). Results are ranked by relevance score.
    Use GET /inspect/{id} to get the full schema for a result before calling it.
    """
    type: str = Field(examples=["operation"], description="Result type: 'operation' for API endpoints, 'workflow' for multi-step Arazzo workflows")
    id: str = Field(examples=["GET/api.github.com/repos/{owner}/{repo}/issues"], description="Capability ID in METHOD/host/path format")
    slug: str | None = Field(default=None, examples=["github-list-issues"], description="Workflow slug (workflows only) — used as path segment in POST /workflows/{slug}")
    summary: str | None = Field(default=None, examples=["List repository issues"], description="Short description of what this capability does")
    description: str | None = Field(default=None, examples=["List issues in a repository"], description="Detailed description from the OpenAPI operation or Arazzo workflow")
    score: float = Field(examples=[0.85], description="BM25 relevance score (0.0-1.0) — higher is more relevant to the search query")
    involved_apis: list[str] = Field(default_factory=list, examples=[["api.github.com"]], description="List of upstream API hosts involved in this capability (for workflows, may list multiple)")
    model_config = {"extra": "allow"}


# ── Capability / inspect (output) ─────────────────────────────────────────────

class CapabilityOut(BaseModel):
    id: str = Field(examples=["GET/api.github.com/repos/{owner}/{repo}/issues"])
    type: str | None = Field(default=None, examples=["operation"])
    summary: str | None = Field(default=None, examples=["List repository issues"])
    description: str | None = Field(default=None, examples=["List issues in a repository. Only issues assigned to the authenticated user are returned."])
    method: str | None = Field(default=None, examples=["GET"])
    path: str | None = Field(default=None, examples=["/repos/{owner}/{repo}/issues"])
    parameters: list[dict] | None = Field(default=None, examples=[[{"name": "owner", "in": "path", "required": True}]])
    request_body: dict | None = Field(default=None, examples=[None])
    responses: dict | None = Field(default=None, examples=[{"200": {"description": "Success"}}])
    security: list[dict] | None = Field(default=None, examples=[[{"bearer": []}]])
    model_config = {"extra": "allow"}


# ── Credentials (output) ──────────────────────────────────────────────────────

class CredentialOut(BaseModel):
    """Upstream API credential metadata. Secret values are never returned after creation."""
    model_config = {"extra": "ignore"}
    id: str = Field(examples=["cred_abc123xyz"])
    label: str = Field(examples=["GitHub PAT for jentic-mini"])
    identity: str | None = Field(default=None, examples=["alice"])
    """Identity field (username, client ID, etc.) — returned so clients can confirm what was stored."""
    api_id: str | None = Field(default=None, examples=["api.github.com"])
    auth_type: str | None = Field(default=None, examples=["bearer"])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    updated_at: float | None = Field(default=None, examples=[1672531200.0])
    account_id: str | None = Field(default=None, examples=["oauth_abc123"])
    app_slug: str | None = Field(default=None, examples=["pipedream"])
    synced_at: float | None = Field(default=None, examples=[1672531200.0])


# ── Toolkits (output) ─────────────────────────────────────────────────────────

class ToolkitKeyOut(BaseModel):
    id: str = Field(examples=["key_abc123xyz"])
    name: str | None = Field(default=None, examples=["Production agent key"])
    prefix: str | None = Field(default=None, examples=["jent_"])
    allowed_ips: list[str] | None = Field(default=None, examples=[["192.168.1.0/24"]])
    revoked: bool = Field(default=False, examples=[False])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    model_config = {"extra": "allow"}


class ToolkitKeyCreated(ToolkitKeyOut):
    """Returned only at key creation — includes the full key value (never returned again)."""
    key: str = Field(examples=["jent_1234567890abcdefghijklmnopqrstuvwxyz"])


class CredentialBindingOut(BaseModel):
    credential_id: str = Field(examples=["cred_abc123xyz"])
    label: str | None = Field(default=None, examples=["GitHub PAT for jentic-mini"])
    api_id: str | None = Field(default=None, examples=["api.github.com"])
    auth_type: str | None = Field(default=None, examples=["bearer"])
    model_config = {"extra": "allow"}


class ToolkitOut(BaseModel):
    """Toolkit configuration with scoped credentials and access control policies."""
    id: str = Field(examples=["default"])
    name: str = Field(examples=["Default Toolkit"])
    description: str | None = Field(default=None, examples=["Default toolkit for general-purpose API access"])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    disabled: bool = Field(default=False, examples=[False])
    key_count: int | None = Field(default=None, examples=[3])
    credential_count: int | None = Field(default=None, examples=[5])
    keys: list[ToolkitKeyOut] = Field(default_factory=list, examples=[[]])
    credentials: list[CredentialBindingOut] = Field(default_factory=list, examples=[[]])
    permissions: list[dict] = Field(default_factory=list, examples=[[{"effect": "allow", "methods": ["GET"]}]])
    model_config = {"extra": "allow"}


# ── Permission rules ──────────────────────────────────────────────────────────

class PermissionRule(BaseModel):
    """A single access control rule. All fields are optional; conditions are AND-combined.
    First matching rule wins. Agent rules are evaluated before system safety rules.

    **`effect`** — `"allow"` or `"deny"` (required)

    **`methods`** — list of HTTP methods to match, e.g. `["GET", "POST"]`.
    Omit to match all methods.

    **`path`** — Python regex matched against the **path component only** of the upstream
    request URL. The host and query string are never included. Matching uses `re.search()`
    (Python), which means:

    - It is always a **regex** — not a glob, not a prefix string.
    - It is **case-insensitive**.
    - It is a **substring match by default** — the pattern can match anywhere in the path
      unless you anchor it with `^` and/or `$`.
    - `|` is regex OR (matches either side).

    **Anchoring guide:**

    | Intent | Pattern | Matches | Does NOT match |
    |--------|---------|---------|----------------|
    | Substring (any path containing word) | `"issues"` | `/repos/x/issues`, `/v1/issues/7` | (nothing — too broad for deny rules) |
    | Prefix (everything under a path) | `"^/repos/jentic/jentic-mini/"` | `/repos/jentic/jentic-mini/issues/34` | `/repos/other/repo/issues` |
    | Exact endpoint | `"^/v1/voices$"` | `/v1/voices` | `/v1/voices/123` |
    | One endpoint + subresources | `"^/repos/jentic/jentic-mini/issues/[0-9]+/comments$"` | `/repos/jentic/jentic-mini/issues/34/comments` | `/repos/jentic/jentic-mini/issues` |
    | Block any sensitive word | `"admin\\|billing\\|pay"` | `/v1/admin/users`, `/billing/invoice` | n/a |

    **Tip for agents generating rules:** always anchor with `^` to avoid unintentionally
    matching longer paths, and use `$` to prevent prefix over-permission. An unanchored
    pattern like `"comments"` would also match `/v1/my-comments-service/admin`.

    **`operations`** — list of regexes matched against the operation ID via `re.search()`.
    E.g. `["tts", "speech"]` matches any operation whose ID contains "tts" or "speech".

    System safety rules (always active, cannot be removed) are marked `_system: true` in
    `GET .../permissions` responses (see `PermissionRuleOut`). They deny sensitive paths
    and write methods by default. The `_system` and `_comment` fields are response-only
    and will be rejected in request bodies.

    **Examples:**
    ```json
    {"effect": "allow", "methods": ["POST"], "path": "^/v1/text-to-speech$"}
    {"effect": "allow", "methods": ["POST"], "path": "^/repos/jentic/jentic-mini/issues/[0-9]+/comments$"}
    {"effect": "allow", "methods": ["GET", "POST"], "path": "^/repos/jentic/jentic-mini/"}
    {"effect": "deny",  "path": "admin|billing|pay"}
    {"effect": "allow", "operations": ["^github_get_repo$"]}
    ```
    """
    effect: Literal["allow", "deny"] = Field(description='`"allow"` or `"deny"`')
    methods: list[str] | None = Field(
        default=None,
        description='HTTP methods to match, e.g. `["GET", "POST"]`. Omit to match all methods.'
    )
    path: str | None = Field(
        default=None,
        description=(
            "Python regex matched with `re.search()` against the **path component only** of the upstream URL "
            "(no host, no query string). Matching is case-insensitive and substring by default — "
            "use `^`/`$` to anchor. `|` is regex OR. "
            "Example: `\"^/repos/jentic/jentic-mini/issues/[0-9]+/comments$\"` matches only that exact endpoint; "
            "omitting anchors would also match any path containing that substring."
        )
    )
    operations: list[str] | None = Field(
        default=None,
        description="List of regexes matched against the operation ID. E.g. `[\"tts\", \"speech\"]`."
    )
    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {"effect": "allow", "methods": ["POST"], "path": "text-to-speech"},
                {"effect": "deny",  "path": "admin|billing|pay"},
                {"effect": "allow", "operations": ["^github_get_repo$"]},
            ]
        }
    }


class PermissionRuleOut(PermissionRule):
    """Permission rule as returned by the API — includes read-only server fields."""
    system: bool | None = Field(default=None, alias="_system")
    comment: str | None = Field(default=None, alias="_comment")
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
    }


class PermissionsPatch(BaseModel):
    """Body for PATCH .../permissions — incremental rule updates."""
    add: list[PermissionRule] = Field(default_factory=list, description="Rules to append (deduplicated by exact match)")
    remove: list[PermissionRule] = Field(default_factory=list, description="Rules to remove by exact match")


# ── Access requests (output) ──────────────────────────────────────────────────

class AccessRequestOut(BaseModel):
    """An access request filed by an agent and awaiting human approval.

    The `payload` shape depends on `type`:

    **`grant`** — bind a new upstream credential to this toolkit (optionally with rules):
    ```json
    { "type": "grant", "payload": { "credential_id": "api.github.com", "rules": [...] }, "reason": "..." }
    ```

    **`modify_permissions`** — update permission rules on an already-bound credential:
    ```json
    { "type": "modify_permissions", "payload": { "credential_id": "api.github.com", "rules": [...] }, "reason": "..." }
    ```
    """
    id: str = Field(examples=["areq_abc123xyz"], description="Unique request ID (areq_xxxxxxxx)")
    toolkit_id: str = Field(examples=["default"], description="The toolkit this request belongs to")
    type: Literal["grant", "modify_permissions", "add_scope"] = Field(
        examples=["grant"],
        description=(
            "`grant` — bind a new upstream API credential to this toolkit (and optionally set permission rules). "
            "`modify_permissions` — update the permission rules on a credential already bound to this toolkit. "
            "`add_scope` — legacy alias for `grant` (deprecated)."
        )
    )
    payload: dict = Field(
        default_factory=dict,
        examples=[{"credential_id": "api.github.com", "rules": [{"effect": "allow", "methods": ["GET"]}]}],
        description=(
            "Request-type-specific data. "
            "For `grant`: `{credential_id, rules?, api_id?}`. "
            "For `modify_permissions`: `{credential_id, rules}`."
        )
    )
    status: Literal["pending", "approved", "denied"] = Field(
        examples=["pending"],
        description="Current approval state. Poll until `approved` or `denied`."
    )
    reason: str | None = Field(default=None, examples=["Need GitHub API access to list repository issues"], description="Human-readable explanation from the agent")
    description: str | None = Field(default=None, examples=["Grant access to api.github.com with GET permissions"], description="Auto-generated summary of what the agent is requesting")
    approve_url: str | None = Field(default=None, examples=["http://localhost:8900/approve/areq_abc123xyz"], description="URL for the human to review and approve/deny")
    created_at: float | None = Field(default=None, examples=[1672531200.0], description="Unix timestamp when filed")
    resolved_at: float | None = Field(default=None, examples=[1672531500.0], description="Unix timestamp when approved or denied")
    applied_effects: list[str] | None = Field(default=None, examples=[["Bound credential api.github.com to toolkit default"]], description="Side-effects applied on approval (credential bound, rules set, etc.)")
    model_config = {"extra": "allow"}


# ── Jobs (output) ─────────────────────────────────────────────────────────────

class JobOut(BaseModel):
    id: str = Field(examples=["job_abc123xyz"])
    kind: str | None = Field(default=None, examples=["workflow"])
    slug_or_id: str | None = Field(default=None, examples=["github-create-issue"])
    toolkit_id: str | None = Field(default=None, examples=["default"])
    status: str = Field(examples=["completed"])
    result: Any = Field(default=None, examples=[{"issue_number": 42, "url": "https://github.com/jentic/jentic-mini/issues/42"}])
    error: str | None = Field(default=None, examples=[None])
    http_status: int | None = Field(default=None, examples=[201])
    upstream_async: bool = Field(default=False, examples=[False])
    upstream_job_url: str | None = Field(default=None, examples=[None])
    trace_id: str | None = Field(default=None, examples=["trace_xyz789"])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    completed_at: float | None = Field(default=None, examples=[1672531205.0])
    model_config = {"extra": "allow"}


class JobListPage(Page):
    data: list[JobOut]


# ── Traces (output) ───────────────────────────────────────────────────────────

class TraceStepOut(BaseModel):
    id: str | None = Field(default=None, examples=["step_1"])
    step_id: str | None = Field(default=None, examples=["getRepo"])
    operation: str | None = Field(default=None, examples=["GET/api.github.com/repos/{owner}/{repo}"])
    status: str | None = Field(default=None, examples=["success"])
    http_status: int | None = Field(default=None, examples=[200])
    output: Any = Field(default=None, examples=[{"name": "jentic-mini", "stars": 42}])
    detail: Any = Field(default=None, examples=[None])
    error: str | None = Field(default=None, examples=[None])
    started_at: float | None = Field(default=None, examples=[1672531200.0])
    completed_at: float | None = Field(default=None, examples=[1672531201.0])
    model_config = {"extra": "allow"}


class TraceOut(BaseModel):
    id: str = Field(examples=["trace_abc123xyz"])
    toolkit_id: str | None = Field(default=None, examples=["default"])
    operation_id: str | None = Field(default=None, examples=["GET/api.github.com/repos/{owner}/{repo}"])
    workflow_id: str | None = Field(default=None, examples=[None])
    spec_path: str | None = Field(default=None, examples=["api.github.com/openapi.json"])
    status: str = Field(examples=["success"])
    http_status: int | None = Field(default=None, examples=[200])
    duration_ms: int | None = Field(default=None, examples=[1234])
    error: str | None = Field(default=None, examples=[None])
    created_at: float | None = Field(default=None, examples=[1672531200.0])
    completed_at: float | None = Field(default=None, examples=[1672531201.0])
    steps: list[TraceStepOut] = Field(default_factory=list, examples=[[]])
    model_config = {"extra": "allow"}


class TraceListPage(BaseModel):
    total: int = Field(examples=[247])
    limit: int = Field(examples=[50])
    offset: int = Field(examples=[0])
    traces: list[TraceOut] = Field(examples=[[]])


# ── Workflows (output) ────────────────────────────────────────────────────────

class WorkflowStepOut(BaseModel):
    id: str | None = Field(default=None, examples=["getRepo"])
    operation: str | None = Field(default=None, examples=["GET/api.github.com/repos/{owner}/{repo}"])
    description: str | None = Field(default=None, examples=["Fetch repository metadata"])
    model_config = {"extra": "allow"}


class WorkflowOut(BaseModel):
    """Multi-step workflow parsed from an Arazzo document.

    Workflows compose multiple API operations into reusable sequences. Each workflow
    is registered in the catalog with a slug and can be executed via POST /workflows/{slug}.
    The workflow runner automatically routes all HTTP calls through the broker for
    credential injection, tracing, and policy enforcement.
    """
    id: str = Field(examples=["POST/localhost:8900/workflows/github-create-issue"], description="Capability ID in format POST/{host}/workflows/{slug}")
    url: str | None = Field(default=None, examples=["http://localhost:8900/workflows/github-create-issue"], description="Absolute URL to execute this workflow via POST")
    slug: str = Field(examples=["github-create-issue"], description="URL-safe workflow identifier used in /workflows/{slug} endpoints")
    name: str | None = Field(default=None, examples=["Create GitHub Issue"], description="Human-readable workflow name from Arazzo info.title or workflow.summary")
    description: str | None = Field(default=None, examples=["Create a new issue in a GitHub repository"], description="Workflow description from Arazzo info.description or workflow.description")
    steps_count: int = Field(default=0, examples=[3], description="Number of steps in this workflow")
    involved_apis: list[str] = Field(default_factory=list, examples=[["api.github.com"]], description="List of upstream API hosts called by this workflow's steps")
    created_at: float | None = Field(default=None, examples=[1672531200.0], description="Unix timestamp when this workflow was imported")
    model_config = {"extra": "allow"}


class WorkflowDetail(WorkflowOut):
    steps: list[WorkflowStepOut] = Field(default_factory=list, examples=[[]])
    input_schema: dict | None = Field(default=None, examples=[{"type": "object", "properties": {"title": {"type": "string"}}}])


# ── Import (output) ───────────────────────────────────────────────────────────

class ImportOut(BaseModel):
    """Result of importing an OpenAPI spec or Arazzo workflow into the catalog.

    The import endpoint (POST /import) accepts specs from URLs, local file paths, or
    inline content. It parses the document, indexes operations/workflows in BM25,
    and stores metadata for broker execution. Returns the registered ID and count
    of indexed operations.
    """
    status: str = Field(examples=["imported"], description="Import status: 'ok' if all sources succeeded, 'partial' if some failed, 'failed' if all failed")
    id: str | None = Field(default=None, examples=["api.github.com"], description="Registered API ID (for OpenAPI specs) or workflow slug (for Arazzo)")
    name: str | None = Field(default=None, examples=["GitHub REST API"], description="Display name extracted from spec (info.title for APIs, workflow.summary for workflows)")
    operations_indexed: int | None = Field(default=None, examples=[247], description="Number of operations parsed and indexed in BM25 (OpenAPI specs only)")
    type: str | None = Field(default=None, examples=["api"], description="Import type: 'api' for OpenAPI specs, 'workflow' for Arazzo documents")
    model_config = {"extra": "allow"}


# ── Default API key (output) ──────────────────────────────────────────────────

class DefaultKeyOut(BaseModel):
    key: str = Field(examples=["jent_1234567890abcdefghijklmnopqrstuvwxyz"])
    toolkit_id: str = Field(examples=["default"])
    setup_url: str | None = Field(default=None, examples=["http://localhost:8900/setup"])
    message: str | None = Field(default=None, examples=["First-time setup key generated. Save this key securely."])
    model_config = {"extra": "allow"}


# ── User / session (input/output) ────────────────────────────────────────────

class TokenRequest(BaseModel):
    """OAuth2 password grant request body for POST /user/token."""
    grant_type: str = Field(default="password", examples=["password"], description="OAuth2 grant type (only 'password' supported)")
    username: str = Field(examples=["admin"], description="User account username")
    password: str = Field(examples=["changeme"], description="User account password")
    scope: str = Field(default="", examples=[""], description="OAuth2 scopes (unused, present for spec compliance)")


class UserOut(BaseModel):
    logged_in: bool = Field(default=False, examples=[True])
    username: str | None = Field(default=None, examples=["admin"])
    is_admin: bool = Field(default=False, examples=[True])
    toolkit_id: str | None = Field(default=None, examples=["default"])
    trusted_subnet: bool = Field(default=False, examples=[True])
    model_config = {"extra": "allow"}
