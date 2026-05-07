"""Shared utility functions for Jentic."""

import re

from src.config import JENTIC_PUBLIC_BASE_URL, JENTIC_PUBLIC_HOSTNAME


def build_absolute_url(request, path: str) -> str:
    """Build an absolute URL from a request and a path.

    Respects X-Forwarded-Proto behind reverse proxies.
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
    return f"{scheme}://{host}{path}"


def build_canonical_url(request, path: str) -> str:
    """Build an absolute URL pinned to the operator-configured public base URL.

    Used by agent-identity routes (issuer, token aud, registration_client_uri)
    so an attacker who can spoof Host:/X-Forwarded-Host: cannot mint or verify
    assertions against an issuer that doesn't match the canonical deployment.

    Falls back to ``build_absolute_url`` when ``JENTIC_PUBLIC_BASE_URL`` is
    unset, preserving the existing dev / on-localhost ergonomics.
    """
    if JENTIC_PUBLIC_BASE_URL:
        return f"{JENTIC_PUBLIC_BASE_URL}{path}"
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
