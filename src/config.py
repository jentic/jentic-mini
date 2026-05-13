"""Centralised configuration constants for Jentic Mini."""

import os
import re
from pathlib import Path
from urllib.parse import urlparse


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

# ── Trusted-proxy forwarded identity ─────────────────────────────────────────
# Both vars must be non-empty to activate the trusted-proxy auth path.
# Either unset → today's JWT-cookie / agent-key behaviour is preserved.
JENTIC_TRUSTED_PROXY_HEADER = os.getenv("JENTIC_TRUSTED_PROXY_HEADER", "")
JENTIC_TRUSTED_PROXY_NETS = os.getenv("JENTIC_TRUSTED_PROXY_NETS", "")


# ── Reverse-proxy path prefix ─────────────────────────────────────────────────
# Optional path at which Mini is mounted behind a reverse proxy (Caddy, Traefik,
# nginx Ingress, etc.). Empty / unset / "/" all mean "no mount" → "". When set,
# the SPA bundle, hand-rolled docs, and self-links resolve under the prefix; if
# unset, the per-request X-Forwarded-Prefix header is honoured. Pair with
# JENTIC_PUBLIC_BASE_URL (which must include the prefix) when mounting.

# Allowlist: one or more "/segment" pairs, each segment is alnum + [-._~]. This
# is the chokepoint that closes the XSS / cookie-injection / stored-URL classes
# from PR #364 review — every char that's dangerous in HTML attributes, inline
# JS strings, or Set-Cookie attribute serialisation (<, >, ", ', ;, ,, \, NUL,
# C0/C1 controls) is rejected here before the value reaches any sink.
_ROOT_PATH_RE = re.compile(r"^(?:/[A-Za-z0-9._~-]+)+/?$")


def normalise_root_path(value: str) -> str:
    """Normalise and validate a path-prefix value.

    Empty string and "/" both mean "no mount" → "". Other values must match
    ``^(?:/[A-Za-z0-9._~-]+)+/?$``. A single trailing slash is stripped
    ("/foo/" → "/foo"); "/foo" is returned unchanged.
    """
    if value in ("", "/"):
        return ""
    # Regex catches metacharacters; segment check catches "." / ".." traversal,
    # which would otherwise match [A-Za-z0-9._~-]+ as a regular segment.
    if not _ROOT_PATH_RE.fullmatch(value) or any(s in (".", "..") for s in value.split("/") if s):
        raise RuntimeError(
            "JENTIC_ROOT_PATH must be /-separated segments of [A-Za-z0-9._~-]+ "
            "(no whitespace, query, fragment, '..', '//', or HTML/JS/cookie "
            "metacharacters)"
        )
    return value[:-1] if value.endswith("/") else value


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

# Fail-fast when the two path-prefix sources disagree. If an operator sets
# JENTIC_PUBLIC_BASE_URL=https://example.com/foo alongside JENTIC_ROOT_PATH=/bar,
# stored URLs (approve_url, OAuth callbacks) embed /foo while request-derived
# URLs embed /bar — silently broken tokens, 404 OAuth callbacks, failed agent
# assertions. Same pattern as the AGENT_NONCE_WINDOW invariant below.
if JENTIC_PUBLIC_BASE_URL:
    _pub_path = urlparse(JENTIC_PUBLIC_BASE_URL).path.rstrip("/")
    if _pub_path != JENTIC_ROOT_PATH.rstrip("/"):
        raise RuntimeError(
            f"JENTIC_PUBLIC_BASE_URL path ({_pub_path!r}) disagrees with "
            f"JENTIC_ROOT_PATH ({JENTIC_ROOT_PATH!r}); both must use the same prefix"
        )

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
