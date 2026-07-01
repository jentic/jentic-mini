"""Toolkit-key resolver — resolves a ``jntc_live_`` key to a toolkit Identity.

A toolkit key authenticates **as the toolkit itself** (broker data plane only):
it bypasses the agent→binding toolkit derivation and names its toolkit directly.
The resolver runs as raw SQL against ``control_db`` (where ``toolkit_keys`` and
``toolkits`` live) because the broker may import neither ``admin`` nor ``control``
ORM — mirroring ``ToolkitBindingResolver``.

The plaintext key is looked up by its deterministic SHA-256 ``lookup_hash`` (the
salted argon2 ``hashed_key`` cannot be queried by value). A revoked key or an
inactive toolkit resolves to ``None`` (→ 401 at the edge).
"""

from __future__ import annotations

import hashlib

from sqlalchemy import text

from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.db import DatabaseSession
from jentic_one.shared.models import ActorType
from jentic_one.shared.scopes import BROKER_EXECUTE_SCOPE

TOOLKIT_KEY_PREFIX = "jntc_live_"

# control DB — resolve a non-revoked key to its active toolkit. The toolkit id
# (tk_…) becomes the Identity subject so attribution/audit/idempotency key off
# the toolkit, and the permission-rule evaluator gates what it may run.
_RESOLVE_TOOLKIT_KEY = text(
    "SELECT t.id AS toolkit_id "
    "FROM toolkit_keys k "
    "JOIN toolkits t ON t.id = k.toolkit_id "
    "WHERE k.lookup_hash = :lookup_hash "
    "  AND k.revoked = false "
    "  AND t.active = true"
)


class ToolkitKeyResolver:
    """Resolves ``jntc_live_`` toolkit keys to a toolkit-scoped Identity.

    Implements ``TokenResolverProtocol`` (via ``resolve_access_token``) so it can
    be wrapped by ``CachedTokenValidator``.
    """

    def __init__(self, control_db: DatabaseSession) -> None:
        self._control_db = control_db

    async def resolve_access_token(self, token: str) -> Identity | None:
        """Protocol method — delegates to prefix-checked resolve."""
        return await self.resolve(token)

    async def resolve(self, raw_key: str) -> Identity | None:
        """Look up a ``jntc_live_`` key and return its toolkit Identity, or None."""
        if not raw_key.startswith(TOOLKIT_KEY_PREFIX):
            return None

        lookup = hashlib.sha256(raw_key.encode()).hexdigest()
        async with self._control_db.session() as session:
            row = (
                await session.execute(_RESOLVE_TOOLKIT_KEY, {"lookup_hash": lookup})
            ).one_or_none()

        if row is None:
            return None

        # A valid toolkit key *is* the execute capability — toolkits carry no
        # actor_scope_grants, so the broker's scope gate is satisfied by granting
        # BROKER_EXECUTE_SCOPE here. Authorization beyond "may execute" is decided
        # by the toolkit permission rules (RuleEvaluator), not by scopes.
        return Identity(
            sub=row.toolkit_id,
            actor_type=ActorType.TOOLKIT,
            permissions=[BROKER_EXECUTE_SCOPE],
            active=True,
        )
