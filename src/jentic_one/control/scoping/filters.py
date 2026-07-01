"""Control-surface access filter builder for dynamic query scoping."""

from __future__ import annotations

from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.sql.elements import ColumnElement

from jentic_one.control.core.schema.access_requests import AccessRequest
from jentic_one.control.core.schema.credentials import Credential
from jentic_one.control.core.schema.toolkit_credential_bindings import ToolkitCredentialBinding
from jentic_one.control.core.schema.toolkit_keys import ToolkitKey
from jentic_one.control.core.schema.toolkit_permission_rules import ToolkitPermissionRule
from jentic_one.control.core.schema.toolkits import Toolkit
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.scopes import (
    ORG_ADMIN,
    OWNER_ACCESS_REQUESTS_READ,
    OWNER_CREDENTIALS_READ,
    OWNER_TOOLKITS_READ,
)

_OWNER_MODELS: dict[type[Any], Any] = {
    Credential: Credential.created_by,
    Toolkit: Toolkit.created_by,
}

_CHILD_MODELS: dict[type[Any], tuple[Any, type[Any], Any, Any]] = {
    ToolkitKey: (ToolkitKey.toolkit_id, Toolkit, Toolkit.id, Toolkit.created_by),
    ToolkitCredentialBinding: (
        ToolkitCredentialBinding.toolkit_id,
        Toolkit,
        Toolkit.id,
        Toolkit.created_by,
    ),
    ToolkitPermissionRule: (
        ToolkitPermissionRule.toolkit_id,
        Toolkit,
        Toolkit.id,
        Toolkit.created_by,
    ),
}

_DELEGATION_SCOPES: dict[type[Any], str] = {
    Credential: OWNER_CREDENTIALS_READ,
    Toolkit: OWNER_TOOLKITS_READ,
    ToolkitKey: OWNER_TOOLKITS_READ,
    ToolkitCredentialBinding: OWNER_TOOLKITS_READ,
    ToolkitPermissionRule: OWNER_TOOLKITS_READ,
    AccessRequest: OWNER_ACCESS_REQUESTS_READ,
}


def build_access_filters(identity: Identity, model: type[Any]) -> list[ColumnElement[bool]]:
    """Build SQLAlchemy filter expressions scoping queries to the caller's visibility.

    Rules (evaluated in order):
    1. org:admin -> no restriction (empty list).
    2. Agent with delegation scope + parent_actor_id -> OR filter.
    3. Otherwise -> owner == self.

    Raises ValueError for an unknown model or empty sub.
    """
    if ORG_ADMIN in identity.permissions:
        return []

    if not identity.sub:
        raise ValueError("empty sub reached scoped read")

    if model in _OWNER_MODELS:
        col = _OWNER_MODELS[model]
        delegation_scope = _DELEGATION_SCOPES.get(model)
        if (
            delegation_scope is not None
            and delegation_scope in identity.permissions
            and identity.parent_actor_id is not None
        ):
            return [or_(col == identity.sub, col == identity.parent_actor_id)]
        return [col == identity.sub]

    if model in _CHILD_MODELS:
        child_fk, _parent_model, parent_pk, parent_owner = _CHILD_MODELS[model]
        delegation_scope = _DELEGATION_SCOPES.get(model)
        if (
            delegation_scope is not None
            and delegation_scope in identity.permissions
            and identity.parent_actor_id is not None
        ):
            owner_clause = or_(
                parent_owner == identity.sub, parent_owner == identity.parent_actor_id
            )
        else:
            owner_clause = parent_owner == identity.sub
        subq = select(parent_pk).where(owner_clause, parent_pk == child_fk)
        return [exists(subq)]

    if model is AccessRequest:
        sub = identity.sub
        delegation_scope = _DELEGATION_SCOPES[AccessRequest]
        if delegation_scope in identity.permissions and identity.parent_actor_id is not None:
            return [
                or_(
                    AccessRequest.created_by == sub,
                    AccessRequest.filer_owner_id == sub,
                    AccessRequest.created_by == identity.parent_actor_id,
                    AccessRequest.filer_owner_id == identity.parent_actor_id,
                )
            ]
        return [
            or_(
                AccessRequest.created_by == sub,
                AccessRequest.filer_owner_id == sub,
            )
        ]

    raise ValueError(f"Unknown model for access scoping: {model.__name__}")


def toolkit_owner_scope(identity: Identity) -> list[str] | None:
    """Return the toolkit owner ids visible to ``identity``, or ``None`` for all.

    ``None`` means an ``org:admin`` decider who may act across every owner. For
    everyone else the scope is their own ``sub`` plus, when they hold the
    toolkit-read delegation scope and have a parent, the parent owner id —
    mirroring :func:`build_access_filters` for the ``Toolkit`` model. Used to
    confine reference-based and explicit ``toolkit:bind`` effects to toolkits
    the decider can actually see.
    """
    if ORG_ADMIN in identity.permissions:
        return None
    if not identity.sub:
        raise ValueError("empty sub reached toolkit owner scope")
    owners = [identity.sub]
    if OWNER_TOOLKITS_READ in identity.permissions and identity.parent_actor_id is not None:
        owners.append(identity.parent_actor_id)
    return owners
