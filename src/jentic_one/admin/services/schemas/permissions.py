"""Permission schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PermissionCatalogueEntry(BaseModel):
    """A single permission in the catalogue."""

    name: str
    description: str
    implies: list[str]
    grantable_by_caller: bool = False


class AssignedPermissionsPayload(BaseModel):
    """Payload for setting user permissions."""

    permissions: list[str]


class PermissionsView(BaseModel):
    """Permissions view for a user."""

    model_config = ConfigDict(from_attributes=True)

    assigned: list[str]
    effective: list[str]
