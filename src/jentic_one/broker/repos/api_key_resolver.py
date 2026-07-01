"""Re-export ApiKeyResolver from shared for backward compatibility."""

from jentic_one.shared.auth.api_key_resolver import (
    AGENT_API_KEY_PREFIX,
    SERVICE_ACCOUNT_API_KEY_PREFIX,
    ApiKeyResolver,
)

__all__ = [
    "AGENT_API_KEY_PREFIX",
    "SERVICE_ACCOUNT_API_KEY_PREFIX",
    "ApiKeyResolver",
]
