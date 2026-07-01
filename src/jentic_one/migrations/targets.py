"""Migration target metadata mapping for all databases."""

from __future__ import annotations

from sqlalchemy import MetaData

import jentic_one.admin.core.schema  # registers admin models on AdminBase.metadata
import jentic_one.control.core.schema  # registers control models on ControlBase.metadata
import jentic_one.registry.core.schema  # noqa: F401  # registers registry models on RegistryBase.metadata
from jentic_one.shared.db.base import AdminBase, ControlBase, RegistryBase

DB_METADATA: dict[str, MetaData] = {
    "registry": RegistryBase.metadata,
    "control": ControlBase.metadata,
    "admin": AdminBase.metadata,
}
