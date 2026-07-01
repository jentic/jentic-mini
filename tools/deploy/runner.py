"""Subprocess wrapper and preflight binary checks."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any


def run(
    *cmd: str, check: bool = True, capture: bool = False, **kwargs: Any
) -> subprocess.CompletedProcess[str]:
    """Run a command, printing it first. Streams output unless capture=True."""
    print(f"\033[36m▸ {' '.join(cmd)}\033[0m", flush=True)
    if capture:
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
    return subprocess.run(cmd, check=check, **kwargs)


def preflight(*binaries: str) -> None:
    """Check that each binary is on $PATH; exit with a clear message if any are missing."""
    missing = [b for b in binaries if shutil.which(b) is None]
    if missing:
        print(f"Error: required tools not found on PATH: {', '.join(missing)}", file=sys.stderr)
        raise SystemExit(1)
