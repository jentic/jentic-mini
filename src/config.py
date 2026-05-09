"""Centralised configuration constants for Jentic Mini."""

import os
from pathlib import Path


# ── Version ───────────────────────────────────────────────────────────────────
# In Docker, APP_VERSION is set via Dockerfile ARG/ENV (CI overrides with
# --build-arg APP_VERSION from the git tag).
APP_VERSION = os.getenv("APP_VERSION", "unknown")

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "/app/data/jentic-mini.db")

# ── Data directories ──────────────────────────────────────────────────────────
_db_path = Path(DB_PATH)
DATA_DIR = _db_path if _db_path.is_dir() else _db_path.parent
SPECS_DIR = DATA_DIR / "specs"
WORKFLOWS_DIR = DATA_DIR / "workflows"

# ── Public hostname ───────────────────────────────────────────────────────────
JENTIC_PUBLIC_HOSTNAME = os.getenv("JENTIC_PUBLIC_HOSTNAME") or "localhost"


# ── Reverse-proxy path prefix ─────────────────────────────────────────────────
# Optional path at which Mini is mounted behind a reverse proxy (Caddy, Traefik,
# nginx Ingress, etc.). Empty / unset / "/" all mean "no mount" → "". When set,
# the SPA bundle, hand-rolled docs, and self-links resolve under the prefix; if
# unset, the per-request X-Forwarded-Prefix header is honoured. Pair with
# JENTIC_PUBLIC_BASE_URL (which must include the prefix) when mounting.
def normalise_root_path(value: str) -> str:
    """Normalise and validate a path-prefix value.

    Empty string and "/" both mean "no mount" → "". Other values must start
    with "/" and contain no whitespace, "?", "#", "..", or consecutive "//".
    A single trailing slash is stripped ("/foo/" → "/foo"); "/foo" is returned
    unchanged. Validation runs against the raw value so "//" surfaces here
    rather than collapsing silently.
    """
    if value in ("", "/"):
        return ""
    if (
        not value.startswith("/")
        or any(ch.isspace() or ch in "?#" for ch in value)
        or ".." in value
        or "//" in value
    ):
        raise RuntimeError(
            "JENTIC_ROOT_PATH must start with '/' and contain no whitespace, "
            "query, fragment, '..', or '//'"
        )
    return value[:-1] if value.endswith("/") and len(value) > 1 else value


JENTIC_ROOT_PATH = normalise_root_path(os.getenv("JENTIC_ROOT_PATH", ""))

# ── Public base URL ───────────────────────────────────────────────────────────
# Operator-pinned canonical base URL (no trailing slash) — e.g.
# "https://jentic.example.com". When set, the issuer / token aud /
# registration_client_uri values used by the agent-identity (OAuth) routes are
# derived from this *only*, ignoring inbound Host: and X-Forwarded-Host:
# headers. Closes the host-header-injection vector where a captured assertion
# minted with a different aud could be replayed against the canonical token
# endpoint by setting Host:.
#
# When unset, those routes fall back to header-derived URLs (existing
# behaviour). Operators on internet-facing deployments are strongly
# encouraged to set this to a fully-qualified URL.
JENTIC_PUBLIC_BASE_URL = (os.getenv("JENTIC_PUBLIC_BASE_URL") or "").rstrip("/")

# ── Toolkit defaults ──────────────────────────────────────────────────────────
DEFAULT_TOOLKIT_ID = "default"


# ── Agent identity (OAuth) ────────────────────────────────────────────────────
def _int_env(name: str, default: int) -> int:
    """Read an int env var, treating unset/empty as the default.

    compose.yml forwards env vars through ``${VAR:-}``, which means an unset
    operator value still arrives as the empty string. ``int("")`` raises, so
    we treat empty-or-unset uniformly here — the operator override is
    unambiguous and a stray blank line in ``.env`` doesn't crash startup.
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


AGENT_ACCESS_TTL = _int_env("AGENT_ACCESS_TTL", 3600)
AGENT_REFRESH_TTL = _int_env("AGENT_REFRESH_TTL", 7 * 24 * 3600)
AGENT_REGISTRATION_TOKEN_TTL = _int_env("AGENT_REGISTRATION_TOKEN_TTL", 900)
AGENT_ASSERTION_MAX_AGE = _int_env("AGENT_ASSERTION_MAX_AGE", 300)
AGENT_NONCE_WINDOW = _int_env("AGENT_NONCE_WINDOW", 600)

# Replay protection invariant: the nonce-cache window must outlive the assertion's
# acceptance window, otherwise a replayed JWT could land after its jti has been
# pruned but before iat falls outside the max-age — silently bypassing the
# replay check. Fail fast at import time so misconfiguration can't ship.
if AGENT_NONCE_WINDOW <= AGENT_ASSERTION_MAX_AGE:
    raise RuntimeError(
        f"AGENT_NONCE_WINDOW ({AGENT_NONCE_WINDOW}s) must be greater than "
        f"AGENT_ASSERTION_MAX_AGE ({AGENT_ASSERTION_MAX_AGE}s) to preserve "
        "JWT-bearer replay protection."
    )
