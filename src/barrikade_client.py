import logging

import httpx

from src.config import (
    BARRIKADE_FAIL_OPEN,
    BARRIKADE_TIMEOUT_MS,
    BARRIKADE_URL,
)


logger = logging.getLogger("jentic.barrikade")


class BarrikadeClient:
    """Asynchronous client for interacting with the Barrikade Security API."""

    @staticmethod
    async def scan_text(text: str) -> dict:
        """Scan text with the Barrikade stateless detection endpoint.

        Returns a dict:
        {
            "is_safe": bool,          # True if no prompt injection/malicious content detected
            "final_verdict": str,      # Barrikade verdict ("pass" or "flag" or "block")
            "decision_layer": str,     # Layer that made the decision
            "confidence_score": float, # Confidence score
            "error": str | None        # Error message if any, otherwise None
        }
        """
        if not BARRIKADE_URL:
            # If Barrikade URL is not configured, treat it as safe/disabled
            return {
                "is_safe": True,
                "final_verdict": "pass",
                "decision_layer": "none",
                "confidence_score": 0.0,
                "error": None,
            }

        # Normalize empty/None text to avoid endpoint validation errors
        if not text or not text.strip():
            return {
                "is_safe": True,
                "final_verdict": "pass",
                "decision_layer": "none",
                "confidence_score": 0.0,
                "error": None,
            }

        url = f"{BARRIKADE_URL}/v1/detect"
        payload = {"text": text, "include_diagnostics": False}
        timeout_sec = BARRIKADE_TIMEOUT_MS / 1000.0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=timeout_sec)

            if response.status_code == 200:
                data = response.json()
                final_verdict = data.get("final_verdict", "pass").lower()
                decision_layer = data.get("decision_layer", "none")
                confidence_score = data.get("confidence_score", 0.0)

                # Verdict is unsafe if it is flagged or blocked
                is_safe = final_verdict not in ("flag", "block", "unsafe", "flagged", "blocked")

                logger.info(
                    "Barrikade scan complete. is_safe=%s verdict=%r layer=%r confidence=%s",
                    is_safe,
                    final_verdict,
                    decision_layer,
                    confidence_score,
                )
                return {
                    "is_safe": is_safe,
                    "final_verdict": final_verdict,
                    "decision_layer": decision_layer,
                    "confidence_score": confidence_score,
                    "error": None,
                }
            else:
                logger.error(
                    "Barrikade API returned error status: %s, body: %r",
                    response.status_code,
                    response.text,
                )
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return {
                    "is_safe": BARRIKADE_FAIL_OPEN,
                    "final_verdict": "pass" if BARRIKADE_FAIL_OPEN else "block",
                    "decision_layer": "error",
                    "confidence_score": 0.0,
                    "error": error_msg,
                }

        except Exception as exc:
            logger.exception("Failed to connect to Barrikade API: %s", exc)
            return {
                "is_safe": BARRIKADE_FAIL_OPEN,
                "final_verdict": "pass" if BARRIKADE_FAIL_OPEN else "block",
                "decision_layer": "error",
                "confidence_score": 0.0,
                "error": str(exc),
            }
