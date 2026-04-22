"""
OAuthBroker — abstract protocol for delegated OAuth credential management.

Implementations:
  PipedreamOAuthBroker  — routes requests through Pipedream Connect proxy
  JenticOAuthBroker     — (future) calls Jentic's own OAuth token service

The broker is consulted by the request broker when no local vault credential
exists for the target API host. It either:
  (a) Returns a raw Bearer token  → inject and forward normally
  (b) Proxies the full request    → hand off entirely, return response

This abstraction exists because:
- OAuth app production approvals take months
- Pipedream already has approvals for 3000+ APIs
- When Jentic gets its own approvals, swap PipedreamOAuthBroker for
  JenticOAuthBroker with zero changes to the broker or API surface
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import httpx


log = logging.getLogger("jentic.oauth_broker")


@runtime_checkable
class OAuthBroker(Protocol):
    """Protocol for OAuth credential management backends."""

    async def covers(self, api_host: str, external_user_id: str) -> bool:
        """Return True if this broker has a connected account for this host + user."""
        ...

    async def get_token(self, api_host: str, external_user_id: str) -> str | None:
        """Return a raw Bearer token, or None if this broker uses proxy mode.

        Proxy mode is used when the OAuth provider (e.g. Pipedream with managed
        OAuth clients) does not expose raw tokens — the request must be routed
        through their proxy instead.
        """
        ...

    async def proxy_request(
        self,
        api_host: str,
        upstream_path: str,
        method: str,
        headers: dict,
        body: bytes,
        query_string: str,
        external_user_id: str,
    ) -> httpx.Response | None:
        """Route the full request through the broker's proxy.

        Return None if this broker does not support proxy mode (i.e. it uses
        get_token instead). The caller will fall through to unauthenticated.
        """
        ...


class OAuthBrokerRegistry:
    """Singleton registry of configured OAuthBroker instances.

    Brokers are loaded from the database at startup and updated
    when brokers are added/removed via the /oauth-brokers API.
    """

    def __init__(self) -> None:
        self._brokers: list[OAuthBroker] = []

    def register(self, broker: OAuthBroker) -> None:
        """Register a broker. Later-registered brokers are tried last."""
        self._brokers.append(broker)

    def deregister(self, broker_id: str) -> None:
        """Remove broker(s) with the given id."""
        self._brokers = [b for b in self._brokers if getattr(b, "broker_id", None) != broker_id]

    def clear(self) -> None:
        self._brokers.clear()

    async def find_broker(self, api_host: str, external_user_id: str) -> OAuthBroker | None:
        """Return the first broker that covers this host + user, or None."""
        for broker in self._brokers:
            try:
                if await broker.covers(api_host, external_user_id):
                    return broker
            except Exception as exc:
                log.warning("OAuthBroker.covers() error for %s: %s", api_host, exc)
        return None

    @property
    def brokers(self) -> list[OAuthBroker]:
        return list(self._brokers)

    def __len__(self) -> int:
        return len(self._brokers)


# Global singleton — imported by broker.py and oauth_brokers router
registry = OAuthBrokerRegistry()
