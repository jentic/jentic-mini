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

# ── Toolkit defaults ──────────────────────────────────────────────────────────
DEFAULT_TOOLKIT_ID = "default"
