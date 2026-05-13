"""Shared utility functions for Jentic."""

import re

from src.config import JENTIC_PUBLIC_BASE_URL, JENTIC_PUBLIC_HOSTNAME, JENTIC_ROOT_PATH


def route_path(scope) -> str:
    """Return ``scope["path"]`` with ``scope["root_path"]`` stripped if applicable.

    Mirrors Starlette's ``get_route_path`` so middleware that compares against
    unprefixed constants (``_SPA_PATHS``, ``_is_public``) keeps working under a
    path prefix. Returns ``"/"`` (not ``""``) when ``path == root_path`` — same
    as Starlette — so the bare mount root (``GET /foo`` with ``root_path=/foo``)
    passes the ``_is_public("/")`` check and renders the SPA. Path stripping is
    otherwise left to Starlette's routing machinery for ``Mount`` / ``StaticFiles``
    cooperation; custom middleware call this helper for the unprefixed view.
    """
    path = scope.get("path", "")
    root_path = scope.get("root_path", "")
    if not root_path or not path.startswith(root_path):
        return path
    if path == root_path:
        # Bare mount root (e.g. GET /foo with root_path=/foo) → treat as "/"
        # so _is_public("/") matches and the SPA handler renders. Matches
        # Starlette's get_route_path return for the same case.
        return "/"
    if path[len(root_path)] == "/":
        return path[len(root_path) :]
    return path


def build_absolute_url(request, path: str) -> str:
    """Build an absolute URL from a request and a path.

    Respects X-Forwarded-Proto behind reverse proxies and prepends the active
    ``root_path`` (from ``JENTIC_ROOT_PATH`` or ``X-Forwarded-Prefix``) so
    self-links resolve under the mount.
    Handles comma-separated values from chained proxies.
    """
    host = (
        (
            request.headers.get("x-forwarded-host")
            or request.headers.get("host")
            or JENTIC_PUBLIC_HOSTNAME
        )
        .split(",")[0]
        .strip()
    )
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    if scheme not in ("http", "https"):
        scheme = "http"
    root_path = request.scope.get("root_path", "") if hasattr(request, "scope") else ""
    return f"{scheme}://{host}{root_path}{path}"


def build_canonical_url(request, path: str) -> str:
    """Build an absolute URL pinned to the operator-configured public base URL.

    Priority:
    1. ``JENTIC_PUBLIC_BASE_URL`` — fully-qualified canonical base (scheme + host + prefix).
    2. ``JENTIC_PUBLIC_HOSTNAME`` when non-default (not ``"localhost"``) — synthesises
       ``https://<hostname><JENTIC_ROOT_PATH><path>``. Covers deployments that set the
       hostname knob but not the full base-URL knob; assumes ``https`` which is correct
       for any internet-facing host.
    3. ``build_absolute_url`` — request-header-derived, correct for local dev where
       ``JENTIC_PUBLIC_HOSTNAME`` is the default ``"localhost"``.

    Used wherever a URL will be consumed outside this process (OAuth callbacks sent to
    Pipedream, approve-links stored in the DB, agent-identity issuer/aud values).
    """
    if JENTIC_PUBLIC_BASE_URL:
        return f"{JENTIC_PUBLIC_BASE_URL}{path}"
    if JENTIC_PUBLIC_HOSTNAME and JENTIC_PUBLIC_HOSTNAME != "localhost":
        return f"https://{JENTIC_PUBLIC_HOSTNAME}{JENTIC_ROOT_PATH}{path}"
    return build_absolute_url(request, path)


# Jentic research: 2 sentences is optimal for tool-selection accuracy.
# We allow 3 (2 + buffer) to avoid cutting meaningful context.
SEARCH_MAX_SENTENCES = 3


def parse_prefer_wait(prefer_header: str | None) -> float | None:
    """Parse RFC 7240 'Prefer: wait=N' header.

    Returns N as a float (seconds), or None if the header is absent or
    does not contain a wait preference.

    Examples:
      "wait=30"           → 30.0
      "respond-async"     → 0.0   (explicit async, no wait)
      "wait=0"            → 0.0
      None                → None  (no preference, block indefinitely)
    """
    if not prefer_header:
        return None
    for part in prefer_header.split(","):
        part = part.strip().lower()
        if part == "respond-async":
            return 0.0
        if part.startswith("wait="):
            try:
                return float(part[5:])
            except ValueError:
                pass
    return None


def workflow_has_async_steps(arazzo_doc: dict) -> bool:
    """Return True if any step in any workflow is tagged x-async: true."""
    for wf in arazzo_doc.get("workflows", []):
        for step in wf.get("steps", []):
            if step.get("x-async") or step.get("x_async"):
                return True
    return False


def abbreviate(text: str | None, max_sentences: int = SEARCH_MAX_SENTENCES) -> str | None:
    """Truncate *text* to at most *max_sentences* sentences.

    Strategy:
    1. Strip template/admonition blocks (e.g. Redocly {% admonition %} syntax).
    2. Split on paragraph breaks (blank lines) OR on '. [A-Z]' within paragraphs.
    3. Keep first *max_sentences* chunks, rejoin, restore terminal period.
    """
    if not text:
        return text
    # Strip {% ... %} template blocks and their content
    clean = re.sub(r"\{%.*?%\}.*?(\{%\s*end\w+\s*%\}|$)", "", text, flags=re.DOTALL)
    clean = re.sub(r"\{%.*?%\}", "", clean, flags=re.DOTALL)
    clean = clean.strip()
    if not clean:
        return text.strip()

    # Split on paragraph breaks first, then on '. [A-Z]' within each paragraph
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", clean) if p.strip()]
    sentences: list[str] = []
    for para in paragraphs:
        parts = re.split(r"\.\s+(?=[A-Z])", para)
        sentences.extend(p.strip() for p in parts if p.strip())

    kept = sentences[:max_sentences]
    result = ". ".join(s.rstrip(".") for s in kept)
    if clean.rstrip().endswith(".") or len(sentences) > max_sentences:
        result = result.rstrip(".") + "."
    return result
