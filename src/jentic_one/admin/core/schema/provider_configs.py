"""ProviderConfigRecord ORM model — runtime, DB-backed credential provider config."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid


class ProviderConfigRecord(AuditableMixin, AdminBase):
    """A runtime-configured credential provider, addressed by provider ``name``.

    Although every config is uniquely keyed by its provider ``name`` (the natural
    key used by the API and registry), the table follows the project's ORM
    convention of a ksuid ``id`` primary key with a unique ``name``. The
    ``config_json`` payload is the full provider configuration with any secret
    fields (e.g. ``client_secret``) **already encrypted** by the service layer —
    plaintext secrets are never persisted. The table is deliberately generic so
    future YAML-backed configs can migrate to the same pattern.
    """

    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("pcfg"),
        server_default=func.generate_ksuid("pcfg"),
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
