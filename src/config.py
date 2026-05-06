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
AGENT_ACCESS_TTL = int(os.getenv("AGENT_ACCESS_TTL", "3600"))
AGENT_REFRESH_TTL = int(os.getenv("AGENT_REFRESH_TTL", str(7 * 24 * 3600)))
AGENT_REGISTRATION_TOKEN_TTL = int(os.getenv("AGENT_REGISTRATION_TOKEN_TTL", "900"))
AGENT_ASSERTION_MAX_AGE = int(os.getenv("AGENT_ASSERTION_MAX_AGE", "300"))
AGENT_NONCE_WINDOW = int(os.getenv("AGENT_NONCE_WINDOW", "600"))

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
