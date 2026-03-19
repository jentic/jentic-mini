"""
Pydantic request / response models for Jentic Mini.
Input models (Create/Patch/Register) and all response models are here.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Credentials (input) ───────────────────────────────────────────────────────

class CredentialCreate(BaseModel):
    label: str
    env_var: str
    """Env var name the broker will use internally. e.g. GITHUB_BEARERAUTH_TOKEN"""
    value: str
    """Plain-text secret; encrypted before storage."""
    api_id: str | None = None
    """API this credential belongs to (e.g. 'techpreneurs.ie'). Required for broker injection."""
    scheme_name: str | None = None
    """Security scheme name from the OpenAPI spec or overlay (e.g. 'ApiKeyHeader'). Required when api_id is set."""


class CredentialPatch(BaseModel):
    label: str | None = None
    value: str | None = None
    api_id: str | None = None
    scheme_name: str | None = None


# ── APIs (input) ──────────────────────────────────────────────────────────────

class ApiRegister(BaseModel):
    id: str | None = None  # auto-derived from spec base_url if omitted
    name: str
    description: str | None = None
    spec_path: str      # absolute path inside container to arazzo/openapi file


# ── Pagination wrapper ────────────────────────────────────────────────────────

class Page(BaseModel):
    """Generic paginated envelope."""
    page: int
    limit: int
    total: int
    total_pages: int
    has_more: bool
    model_config = {"extra": "allow"}


# ── APIs (output) ─────────────────────────────────────────────────────────────

class ApiOut(BaseModel):
    id: str
    name: str | None = None
    vendor: str | None = None
    description: str | None = None
    spec_path: str | None = None
    base_url: str | None = None
    created_at: float | None = None
    model_config = {"extra": "allow"}


class OperationOut(BaseModel):
    """A single API operation. id encodes method/host/path (capability ID format)."""
    id: str
    summary: str | None = None
    description: str | None = None
    model_config = {"extra": "allow"}


class ApiListPage(Page):
    data: list[ApiOut]


class OperationListPage(Page):
    data: list[OperationOut]


# ── Search (output) ───────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    type: str  # "operation" | "workflow"
    id: str
    slug: str | None = None
    summary: str | None = None
    description: str | None = None
    score: float
    involved_apis: list[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}


# ── Capability / inspect (output) ─────────────────────────────────────────────

class CapabilityOut(BaseModel):
    id: str
    type: str | None = None
    summary: str | None = None
    description: str | None = None
    method: str | None = None
    path: str | None = None
    parameters: list[dict] | None = None
    request_body: dict | None = None
    responses: dict | None = None
    security: list[dict] | None = None
    model_config = {"extra": "allow"}


# ── Credentials (output) ──────────────────────────────────────────────────────

class CredentialOut(BaseModel):
    model_config = {"extra": "ignore"}
    id: str
    label: str
    api_id: str | None = None
    scheme_name: str | None = None
    created_at: float | None = None
    updated_at: float | None = None
    created_at: float | None = None
    updated_at: float | None = None
    model_config = {"extra": "allow"}


# ── Toolkits (output) ─────────────────────────────────────────────────────────

class ToolkitKeyOut(BaseModel):
    id: str
    name: str | None = None
    prefix: str | None = None
    allowed_ips: list[str] | None = None
    revoked: bool = False
    created_at: float | None = None
    model_config = {"extra": "allow"}


class ToolkitKeyCreated(ToolkitKeyOut):
    """Returned only at key creation — includes the full key value (never returned again)."""
    key: str


class CredentialBindingOut(BaseModel):
    credential_id: str
    label: str | None = None
    api_id: str | None = None
    scheme_name: str | None = None
    model_config = {"extra": "allow"}


class ToolkitOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: float | None = None
    keys: list[ToolkitKeyOut] = Field(default_factory=list)
    credentials: list[CredentialBindingOut] = Field(default_factory=list)
    permissions: list[dict] = Field(default_factory=list)
    model_config = {"extra": "allow"}


# ── Permission rules ──────────────────────────────────────────────────────────

class PermissionRule(BaseModel):
    """A single access control rule. All fields are optional; conditions are AND-combined.
    First matching rule wins. Agent rules are evaluated before system safety rules.

    **`effect`** — `"allow"` or `"deny"` (required)

    **`methods`** — list of HTTP methods to match, e.g. `["GET", "POST"]`.
    Omit to match all methods.

    **`path`** — Python regex matched with `re.search()` against the upstream request path.
    This is a **substring match** — `"admin|pay"` matches any path *containing* those words.
    Case-insensitive. Use `^`/`$` to anchor. `|` is regex OR.

    Examples:
    - `"admin|billing|pay"` — matches `/v1/admin/users`, `/billing/invoice`, `/pay`
    - `"^/v1/voices$"` — matches only exactly `/v1/voices`
    - `"text-to-speech"` — matches any path containing that substring

    **`operations`** — list of regexes matched against the operation ID via `re.search()`.
    E.g. `["tts", "speech"]` matches any operation whose ID contains "tts" or "speech".

    System safety rules (always active, cannot be removed) are marked `_system: true` in
    `GET .../permissions` responses. They deny sensitive paths and write methods by default.

    **Examples:**
    ```json
    {"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}
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
            "Python regex matched with `re.search()` (substring, case-insensitive) against the upstream path. "
            "`|` is OR. Use `^`/`$` to anchor. Example: `\"text-to-speech\"` matches any path containing that string."
        )
    )
    operations: list[str] | None = Field(
        default=None,
        description="List of regexes matched against the operation ID. E.g. `[\"tts\", \"speech\"]`."
    )
    # Read-only server fields on system rules (ignored on write)
    model_config = {
        "extra": "allow",  # allows _system/_comment through in responses
        "json_schema_extra": {
            "examples": [
                {"effect": "allow", "methods": ["POST"], "path": "text-to-speech"},
                {"effect": "deny",  "path": "admin|billing|pay"},
                {"effect": "allow", "operations": ["^github_get_repo$"]},
            ]
        }
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
    id: str = Field(description="Unique request ID (areq_xxxxxxxx)")
    toolkit_id: str = Field(description="The toolkit this request belongs to")
    type: Literal["grant", "modify_permissions"] = Field(
        description=(
            "`grant` — bind a new upstream API credential to this toolkit (and optionally set permission rules). "
            "`modify_permissions` — update the permission rules on a credential already bound to this toolkit."
        )
    )
    payload: dict = Field(
        default_factory=dict,
        description=(
            "Request-type-specific data. "
            "For `grant`: `{credential_id, rules?, api_id?}`. "
            "For `modify_permissions`: `{credential_id, rules}`."
        )
    )
    status: Literal["pending", "approved", "denied"] = Field(
        description="Current approval state. Poll until `approved` or `denied`."
    )
    reason: str | None = Field(default=None, description="Human-readable explanation from the agent")
    description: str | None = Field(default=None, description="Auto-generated summary of what the agent is requesting")
    approve_url: str | None = Field(default=None, description="URL for the human to review and approve/deny")
    created_at: float | None = Field(default=None, description="Unix timestamp when filed")
    resolved_at: float | None = Field(default=None, description="Unix timestamp when approved or denied")
    applied_effects: list[str] | None = Field(default=None, description="Side-effects applied on approval (credential bound, rules set, etc.)")
    model_config = {"extra": "allow"}


# ── Jobs (output) ─────────────────────────────────────────────────────────────

class JobOut(BaseModel):
    id: str
    kind: str | None = None
    slug_or_id: str | None = None
    toolkit_id: str | None = None
    status: str
    result: Any = None
    error: str | None = None
    http_status: int | None = None
    upstream_async: bool = False
    upstream_job_url: str | None = None
    trace_id: str | None = None
    created_at: float | None = None
    completed_at: float | None = None
    model_config = {"extra": "allow"}


class JobListPage(Page):
    data: list[JobOut]


# ── Traces (output) ───────────────────────────────────────────────────────────

class TraceStepOut(BaseModel):
    id: str | None = None
    step_id: str | None = None
    operation: str | None = None
    status: str | None = None
    http_status: int | None = None
    output: Any = None
    detail: Any = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    model_config = {"extra": "allow"}


class TraceOut(BaseModel):
    id: str
    toolkit_id: str | None = None
    operation_id: str | None = None
    workflow_id: str | None = None
    spec_path: str | None = None
    status: str
    http_status: int | None = None
    duration_ms: int | None = None
    error: str | None = None
    created_at: float | None = None
    completed_at: float | None = None
    steps: list[TraceStepOut] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class TraceListPage(BaseModel):
    total: int
    limit: int
    offset: int
    traces: list[TraceOut]


# ── Workflows (output) ────────────────────────────────────────────────────────

class WorkflowStepOut(BaseModel):
    id: str | None = None
    operation: str | None = None
    description: str | None = None
    model_config = {"extra": "allow"}


class WorkflowOut(BaseModel):
    id: str
    url: str | None = None
    slug: str
    name: str | None = None
    description: str | None = None
    steps_count: int = 0
    involved_apis: list[str] = Field(default_factory=list)
    created_at: float | None = None
    model_config = {"extra": "allow"}


class WorkflowDetail(WorkflowOut):
    steps: list[WorkflowStepOut] = Field(default_factory=list)
    input_schema: dict | None = None


# ── Import (output) ───────────────────────────────────────────────────────────

class ImportOut(BaseModel):
    status: str
    id: str | None = None
    name: str | None = None
    operations_indexed: int | None = None
    type: str | None = None  # "api" | "workflow"
    model_config = {"extra": "allow"}


# ── Default API key (output) ──────────────────────────────────────────────────

class DefaultKeyOut(BaseModel):
    key: str
    toolkit_id: str
    setup_url: str | None = None
    message: str | None = None
    model_config = {"extra": "allow"}


# ── User / session (output) ───────────────────────────────────────────────────

class UserOut(BaseModel):
    logged_in: bool = False
    username: str | None = None
    is_admin: bool = False
    toolkit_id: str | None = None
    trusted_subnet: bool = False
    model_config = {"extra": "allow"}
