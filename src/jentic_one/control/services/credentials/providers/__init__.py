"""Credential provider protocol, registry, and built-in implementations."""

from jentic_one.control.services.credentials.providers.base import (
    CredentialProvider,
    NotConnectableError,
    NotRefreshableError,
    ProviderError,
    UnknownProviderError,
)
from jentic_one.control.services.credentials.providers.direct_oauth2 import (
    DirectOAuth2Provider,
    InvalidGrantError,
    TokenExchangeError,
)
from jentic_one.control.services.credentials.providers.pipedream import (
    PipedreamAPIError,
    PipedreamProvider,
)
from jentic_one.control.services.credentials.providers.registry import ProviderRegistry
from jentic_one.control.services.credentials.providers.static import StaticProvider

__all__ = [
    "CredentialProvider",
    "DirectOAuth2Provider",
    "InvalidGrantError",
    "NotConnectableError",
    "NotRefreshableError",
    "PipedreamAPIError",
    "PipedreamProvider",
    "ProviderError",
    "ProviderRegistry",
    "StaticProvider",
    "TokenExchangeError",
    "UnknownProviderError",
]
