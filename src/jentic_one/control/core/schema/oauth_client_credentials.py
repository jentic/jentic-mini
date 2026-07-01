"""OAuthClientCredential ORM model for OAuth2 client credentials flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jentic_one.shared.db.base import AuditableMixin, ControlBase

if TYPE_CHECKING:
    from jentic_one.control.core.schema.credentials import Credential


class OAuthClientCredential(AuditableMixin, ControlBase):
    """Stores OAuth2 client credentials (client ID + encrypted secret)."""

    __tablename__ = "oauth_client_credentials"

    id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("credentials.id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_client_secret: Mapped[str] = mapped_column(Text, nullable=False)
    authorize_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    credential: Mapped[Credential] = relationship(back_populates="oauth_client_credential")
