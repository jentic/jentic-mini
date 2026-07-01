"""Result models for toolkit credential binding queries."""

from __future__ import annotations

from pydantic import BaseModel

from jentic_one.control.core.schema.toolkit_credential_bindings import ToolkitCredentialBinding
from jentic_one.control.core.schema.toolkit_permission_rules import ToolkitPermissionRule


class BindingWithPermissions(BaseModel):
    """A binding paired with its permission rules."""

    model_config = {"arbitrary_types_allowed": True}

    binding: ToolkitCredentialBinding
    rules: list[ToolkitPermissionRule]


class BindingPage(BaseModel):
    """Paginated list of bindings with their permissions."""

    model_config = {"arbitrary_types_allowed": True}

    data: list[BindingWithPermissions]
    has_more: bool
    next_cursor: str | None = None
