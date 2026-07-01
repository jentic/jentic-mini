"""Consolidated JWKS key caching — single source for key construction and resolution."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jwt.algorithms import OKPAlgorithm

from jentic_one.shared.config import AuthConfig
from jentic_one.shared.crypto import ec_public_key_to_jwk, load_es256_private_key


class CachedJWKSPublisher:
    """Builds and caches the server's JWKS document from configured ES256 signing keys.

    Keys are static config, so the document is computed once on first access.
    """

    def __init__(self, config: AuthConfig) -> None:
        self._config = config
        self._cached: dict[str, list[dict[str, str]]] | None = None

    def get_jwks(self) -> dict[str, list[dict[str, str]]]:
        """Return the JWKS document, building it on first call."""
        if self._cached is None:
            self._cached = self._build()
        return self._cached

    def _build(self) -> dict[str, list[dict[str, str]]]:
        keys: list[dict[str, str]] = []
        for key_config in self._config.id_signing:
            private_key = load_es256_private_key(key_config)
            pub = private_key.public_key()
            keys.append(ec_public_key_to_jwk(pub, key_config.kid))
        return {"keys": keys}


@lru_cache(maxsize=128)
def _resolve_cached(jwks_fingerprint: str, kid: str | None) -> Any:
    """LRU-cached key resolution keyed on JWKS content + kid."""
    jwks: dict[str, Any] = json.loads(jwks_fingerprint)
    return _do_resolve(jwks, kid)


def _do_resolve(jwks: dict[str, Any], kid: str | None) -> Any:
    """Resolve an Ed25519 public key from a JWKS dict."""
    keys = jwks.get("keys", [])
    for key_data in keys:
        if key_data.get("kty") != "OKP" or key_data.get("crv") != "Ed25519":
            continue
        if kid is not None and key_data.get("kid") != kid:
            continue
        try:
            algo = OKPAlgorithm()
            return algo.from_jwk(key_data)
        except Exception:
            continue
    return None


def resolve_agent_key(jwks: dict[str, Any], kid: str | None = None) -> Any:
    """Resolve an Ed25519 public key from an agent's stored JWKS.

    Results are cached by JWKS content and kid so repeated verifications
    for the same agent skip deserialization.
    """
    fingerprint = json.dumps(jwks, sort_keys=True)
    return _resolve_cached(fingerprint, kid)
