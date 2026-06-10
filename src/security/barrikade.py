"""Barrikade prompt-injection scanner"""

import logging

import httpx

from src.security.plugin import SecurityPlugin, SecurityVerdict


logger = logging.getLogger("jentic.security.barrikade")


class BarrikadePlugin(SecurityPlugin):
    """Barrikade prompt-injection scanner plugin.

    Calls the Barrikade ``/v1/detect`` endpoint to classify text.
    All configuration (URL, timeout, fail-open policy) is injected at
    construction time -  this class reads nothing from the environment.
    """

    name = "barrikade"

    def __init__(self, url: str, timeout_ms: int = 30000, fail_open: bool = True):
        self._url = url.rstrip("/")
        self._timeout_sec = timeout_ms / 1000.0
        self._fail_open = fail_open

    async def scan_text(self, text: str) -> SecurityVerdict:
        """Scan text via the Barrikade stateless detection endpoint."""
        # Skip empty / whitespace-only input
        if not text or not text.strip():
            return SecurityVerdict(
                is_safe=True,
                verdict="pass",
                decision_layer="none",
                confidence_score=0.0,
                plugin_name=self.name,
            )

        url = f"{self._url}/v1/detect"
        payload = {"text": text, "include_diagnostics": False}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=self._timeout_sec)

            if response.status_code == 200:
                data = response.json()
                final_verdict = data.get("final_verdict", "pass").lower()
                decision_layer = data.get("decision_layer", "none")
                confidence_score = data.get("confidence_score", 0.0)

                is_safe = final_verdict not in (
                    "flag",
                    "block",
                    "unsafe",
                    "flagged",
                    "blocked",
                )

                logger.info(
                    "Barrikade scan complete. is_safe=%s verdict=%r layer=%r confidence=%s",
                    is_safe,
                    final_verdict,
                    decision_layer,
                    confidence_score,
                )
                return SecurityVerdict(
                    is_safe=is_safe,
                    verdict=final_verdict,
                    decision_layer=decision_layer,
                    confidence_score=confidence_score,
                    plugin_name=self.name,
                )
            else:
                logger.error(
                    "Barrikade API returned error status: %s, body: %r",
                    response.status_code,
                    response.text,
                )
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return SecurityVerdict(
                    is_safe=self._fail_open,
                    verdict="pass" if self._fail_open else "block",
                    decision_layer="error",
                    confidence_score=0.0,
                    plugin_name=self.name,
                    error=error_msg,
                )

        except Exception as exc:
            logger.exception("Failed to connect to Barrikade API: %s", exc)
            return SecurityVerdict(
                is_safe=self._fail_open,
                verdict="pass" if self._fail_open else "block",
                decision_layer="error",
                confidence_score=0.0,
                plugin_name=self.name,
                error=str(exc),
            )

    def should_scan_ingress(self, path: str, method: str) -> bool:
        """Only scan Jentic search, workflow trigger, and broker ingress paths."""
        normalized_path = path.lstrip("/")
        first_segment = normalized_path.split("/")[0] if normalized_path else ""
        return (
            path == "/search"
            or (path.startswith("/workflows/") and method == "POST")
            or "." in first_segment
        )

    def should_scan_response(self, host: str, status_code: int) -> bool:
        """Scan all upstream API responses."""
        return True
