"""CatalogSnapshot ORM model — the public API catalog cached as a single blob.

The catalog is a wholesale-replaced, read-mostly, relationship-free mirror of an
upstream GitHub ``apis.json`` manifest. It is therefore modelled as **one row**
holding the whole parsed manifest as a JSON document, rather than one row per
entry. This keeps the operational wins of living in the DB (shared across
replicas, atomic refresh, survives redeploy, migratable) while dropping the costs
of the per-row table (truncate/insert churn of ~1k rows on every refresh, ORM
hydration of a thousand objects per browse, a fragile ``MAX(created_at)``
freshness probe, and dead indexes never used in a WHERE).

A refresh upserts the single snapshot row (fixed primary key, see
``SINGLETON_ID``) in one transaction, so there is **structurally** at most one
current snapshot — a second concurrent refresh collides on the primary key
rather than leaving a duplicate row behind. Freshness is the explicit
``created_at`` column (rewritten to the fetch time on every refresh) — not
inferred from any aggregate over many rows.

The ``id`` is an internal, constant row identifier only; it is **never** an
import identifier and never crosses into the importer (see D-005a).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import RegistryBase
from jentic_one.shared.db.types import UTCDateTime, json_variant
from jentic_one.shared.db.utils import utcnow

#: Fixed primary key of the one-and-only catalog snapshot row. Using a constant
#: id makes the table structurally single-row: a concurrent refresh that races to
#: insert collides on this key instead of appending a second snapshot.
SINGLETON_ID = "catalog"


class CatalogSnapshot(RegistryBase):
    """A single cached snapshot of the upstream catalog manifest.

    ``entries`` is the parsed manifest as a list of plain dicts, each with the
    shape produced by ``manifest_builder.ManifestEntry`` (``api_id``, ``vendor``,
    ``path``, ``spec_url``, ``github_url``). The service projects these into views;
    nothing queries inside the blob at the DB level (the dataset is ~1 MB).

    ``created_at`` doubles as the manifest fetch time (rewritten on every refresh)
    and is the freshness signal the service reads for lazy refresh-on-read.
    """

    __tablename__ = "catalog_snapshots"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=SINGLETON_ID)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entries: Mapped[list[dict[str, Any]]] = mapped_column(json_variant(), nullable=False)
