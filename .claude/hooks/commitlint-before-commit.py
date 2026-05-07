#!/usr/bin/env python3
# PreToolUse hook: validate Conventional Commits before Claude fires `git commit`.
# Reads Claude Code's tool-input JSON from stdin. On a malformed message, emits
# a `permissionDecision: deny` JSON so the bash command never runs.
# Mirrors what .husky/commit-msg enforces for human/CI commits.
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITLINT_BIN = REPO_ROOT / "ui" / "node_modules" / ".bin" / "commitlint"


def emit_deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def extract_message(command: str) -> str | None:
    # Pattern: -m "$(cat <<'DELIM' ... DELIM)" — what Claude's CLAUDE.md prescribes.
    m = re.search(
        r"-m\s+\"?\$\(\s*cat\s+<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n\s*\1\s*\n",
        command,
        re.DOTALL,
    )
    if m:
        return textwrap.dedent(m.group(2))
    # Pattern: -m "..." with escapes
    m = re.search(r'-m\s+"((?:[^"\\]|\\.)*)"', command)
    if m:
        return m.group(1).encode("utf-8").decode("unicode_escape")
    # Pattern: -m '...' (single quotes — no escapes in shell)
    m = re.search(r"-m\s+'([^']*)'", command)
    if m:
        return m.group(1)
    return None


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return 0

    command = data.get("tool_input", {}).get("command", "") or ""

    if not re.search(r"(^|[\s&;|])git\s+commit(\s|$)", command):
        return 0
    if "--no-edit" in command:
        return 0
    if not COMMITLINT_BIN.exists():
        # Fresh checkout before `npm install` — defer to husky.
        return 0

    msg = extract_message(command)
    if not msg:
        # Couldn't extract (e.g., -F file or interactive editor); husky covers it.
        return 0

    try:
        proc = subprocess.run(
            [str(COMMITLINT_BIN)],
            input=msg,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT / "ui"),
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0

    if proc.returncode == 0:
        return 0

    output = (proc.stdout + proc.stderr).strip() or "commitlint reported errors."
    emit_deny(
        "Commit message fails Conventional Commits validation "
        "(see .claude/rules/conventional-commits.md):\n\n" + output
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
