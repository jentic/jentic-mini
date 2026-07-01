"""CatalogService — orchestrates the public API catalog (browse / preview / import).

Layering: this service is the only thing in the catalog slice that touches I/O —
the upstream GitHub manifest + spec fetches (``fetch.py``), the catalog cache DB
(``CatalogRepository``), and the import job queue (``enqueue_job``). All parsing /
projection is delegated to the pure ``manifest_builder`` lib so this file stays
about coordination.

Boundaries kept from D-005a:
- imports always resolve to a plain url ``IngestSource`` — no ``cat_…`` opaque IDs
  cross into the importer, no ``ApiSourceCatalog`` discriminator, no ``force_api_id``.
- identity is the spec triple (vendor/name/version) resolved by the importer, so a
  re-import maps onto the same local API.
- APIs only — workflows are out of scope (D-001).
- imports are async (job-poll), never a synchronous swap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jentic_one.registry.repos.catalog_repo import CatalogRepository
from jentic_one.registry.services.catalog import manifest_builder as mb
from jentic_one.registry.services.catalog.fetch import CatalogFetchError, fetch_json
from jentic_one.registry.services.errors import (
    CatalogEntryNotFoundError,
    CatalogUnavailableError,
)
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.db.utils import utcnow
from jentic_one.shared.jobs.enqueue import enqueue_job
from jentic_one.shared.models.jobs import JobKind
from jentic_one.shared.pagination import decode_catalog_cursor, encode_catalog_cursor


@dataclass(frozen=True)
class CatalogEntryView:
    """A browsable catalog entry with derived `registered` status."""

    api_id: str
    vendor: str | None
    path: str | None
    spec_url: str | None
    github_url: str | None
    registered: bool


@dataclass(frozen=True)
class CatalogListView:
    """A page of catalog entries plus the status fields the UI status row needs."""

    data: list[CatalogEntryView]
    catalog_total: int
    registered_count: int
    manifest_age_seconds: int | None
    has_more: bool
    next_cursor: str | None


@dataclass(frozen=True)
class CatalogPreviewView:
    """A capped, offset-paginated preview of an entry's operations."""

    operations: list[mb.PreviewOperation]
    total: int
    offset: int
    truncated: bool
    info: mb.PreviewInfo
    security_schemes: dict[str, dict[str, object]]


@dataclass(frozen=True)
class CatalogRefreshResult:
    """Outcome of a manifest refresh."""

    count: int


class CatalogService:
    """Read + import operations for the public API catalog."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx
        self._cfg = ctx.config.catalog
        self._ingest_cfg = ctx.config.ingest

    # ── refresh / staleness ──────────────────────────────────────────────────

    async def refresh(self) -> CatalogRefreshResult:
        """Fetch the upstream manifest and atomically replace the catalog snapshot."""
        try:
            doc = await fetch_json(self._cfg.manifest_url, config=self._ingest_cfg)
        except CatalogFetchError as exc:
            raise CatalogUnavailableError(f"catalog manifest unavailable: {exc}") from exc

        entries = [e.to_dict() for e in mb.parse_apis_json(doc)]
        async with self._ctx.registry_db.transaction() as session:
            count = await CatalogRepository.replace(
                session, source_url=self._cfg.manifest_url, entries=entries
            )
        return CatalogRefreshResult(count=count)

    def _is_stale(self, fetched_at: datetime | None) -> bool:
        """Whether the cache should be lazily refreshed (D-005a option (a)).

        Stale when empty or older than ``manifest_max_age_seconds``. A max-age of
        0 disables auto-refresh (manual ``:refresh`` only).
        """
        if self._cfg.manifest_max_age_seconds <= 0:
            return False
        if fetched_at is None:
            return True
        return (utcnow() - fetched_at).total_seconds() > self._cfg.manifest_max_age_seconds

    async def _safe_refresh(self) -> None:
        """Refresh with advisory-lock single-flight, swallowing upstream failures.

        Only the first concurrent caller acquires the lock and performs the
        upstream fetch; others return immediately and serve the current snapshot.
        """
        async with self._ctx.registry_db.transaction() as session:
            acquired = await CatalogRepository.try_acquire_refresh_lock(session)
            if not acquired:
                return
            fetched_at = await CatalogRepository.fetched_at(session)
            if not self._is_stale(fetched_at):
                return
        try:
            await self.refresh()
        except CatalogUnavailableError:
            return

    async def _refresh_if_stale(self) -> None:
        """Lazy refresh-on-read seam for the single-entry reads (``get``)."""
        async with self._ctx.registry_db.session() as session:
            fetched_at = await CatalogRepository.fetched_at(session)
        if self._is_stale(fetched_at):
            await self._safe_refresh()

    async def _load_snapshot(self) -> tuple[list[dict[str, Any]], set[str], datetime | None]:
        """Read the snapshot entries, coverage URLs, and freshness in one session."""
        async with self._ctx.registry_db.session() as session:
            raw = await CatalogRepository.entries(session)
            registered_urls = await CatalogRepository.registered_spec_urls(session)
            fetched_at = await CatalogRepository.fetched_at(session)
        return raw, registered_urls, fetched_at

    # ── browse / get ─────────────────────────────────────────────────────────

    async def list_all(
        self,
        *,
        q: str | None = None,
        registered_only: bool = False,
        unregistered_only: bool = False,
        cursor: str | None = None,
        limit: int = 50,
    ) -> CatalogListView:
        """List a keyset page of catalog entries (optionally filtered/ranked).

        Paging is an in-memory keyset over the cached snapshot blob: entries are
        ordered (``api_id`` for browse, ``(-score, api_id)`` for search), the
        registration filter is applied, then a ``limit``-sized window after the
        ``cursor`` position is returned. ``catalog_total``/``registered_count``
        always reflect the full manifest (pre-filter, pre-page) so the UI status
        row is stable across pages. Raises ``InvalidCursorError`` on a bad cursor.

        A cursor is only meaningful for the **same** ``(q, registered_only,
        unregistered_only)`` it was issued under — it encodes a position in that
        specific ordering, not the query — so callers must hold those constant
        while paging (changing them mid-scroll yields a valid but meaningless
        slice, never an error). Cursors are also relative to the snapshot at read
        time: a refresh between pages may skip/repeat entries near the cursor
        (the standard keyset-vs-mutating-snapshot trade-off), but never crashes
        or loops. Refresh is rare (lazy, max-age gated), so this is acceptable.
        """
        raw, registered_urls, fetched_at = await self._load_snapshot()
        if self._is_stale(fetched_at):
            await self._safe_refresh()
            raw, registered_urls, fetched_at = await self._load_snapshot()

        all_entries = [mb.ManifestEntry.from_dict(d) for d in raw]
        catalog_total = len(all_entries)
        registered_count = sum(1 for e in all_entries if mb.is_registered(e, registered_urls))

        scored = mb.score_entries(all_entries, q)
        if registered_only:
            scored = [(e, s) for e, s in scored if mb.is_registered(e, registered_urls)]
        elif unregistered_only:
            scored = [(e, s) for e, s in scored if not mb.is_registered(e, registered_urls)]

        after_api_id, after_score = decode_catalog_cursor(cursor) if cursor else (None, None)
        page = mb.paginate_entries(
            scored, after_api_id=after_api_id, after_score=after_score, limit=limit
        )
        views = [self._to_view(e, registered_urls) for e in page.items]
        next_cursor = (
            encode_catalog_cursor(page.next_api_id, page.next_score)
            if page.has_more and page.next_api_id is not None
            else None
        )

        age = None if fetched_at is None else int((utcnow() - fetched_at).total_seconds())
        return CatalogListView(
            data=views,
            catalog_total=catalog_total,
            registered_count=registered_count,
            manifest_age_seconds=age,
            has_more=page.has_more,
            next_cursor=next_cursor,
        )

    async def get(self, api_id: str) -> CatalogEntryView:
        """Resolve a single catalog entry by api_id."""
        await self._refresh_if_stale()
        async with self._ctx.registry_db.session() as session:
            raw = await CatalogRepository.entries(session)
            registered_urls = await CatalogRepository.registered_spec_urls(session)
        match = next((d for d in raw if d.get("api_id") == api_id), None)
        if match is None:
            raise CatalogEntryNotFoundError(api_id)
        return self._to_view(mb.ManifestEntry.from_dict(match), registered_urls)

    @staticmethod
    def _to_view(entry: mb.ManifestEntry, registered_spec_urls: set[str]) -> CatalogEntryView:
        return CatalogEntryView(
            api_id=entry.api_id,
            vendor=entry.vendor,
            path=entry.path or None,
            spec_url=entry.spec_url,
            github_url=entry.github_url or None,
            registered=mb.is_registered(entry, registered_spec_urls),
        )

    # ── preview ──────────────────────────────────────────────────────────────

    async def preview(
        self,
        api_id: str,
        *,
        offset: int = 0,
        limit: int = mb.PREVIEW_MAX_OPERATIONS,
        tag: str | None = None,
        q: str | None = None,
    ) -> CatalogPreviewView:
        """Fetch the entry's spec and project a capped, paginated operation list.

        ``tag`` and ``q`` filter the full operation set server-side *before*
        windowing, so the search box / tag chips in the UI cover every operation
        in the spec — not just the loaded page — and ``total`` reflects the
        filtered count the "Load more" affordance pages through.
        """
        entry = await self.get(api_id)
        if not entry.spec_url:
            raise CatalogUnavailableError(f"catalog entry '{api_id}' has no spec url")
        try:
            doc = await fetch_json(entry.spec_url, config=self._ingest_cfg)
        except CatalogFetchError as exc:
            raise CatalogUnavailableError(f"catalog spec unavailable: {exc}") from exc

        projection = mb.project_preview(doc, tag=tag, q=q)
        total = len(projection.operations)
        capped_limit = max(0, min(limit, mb.PREVIEW_MAX_OPERATIONS))
        start = max(0, offset)
        window = projection.operations[start : start + capped_limit]
        return CatalogPreviewView(
            operations=window,
            total=total,
            offset=start,
            truncated=start + len(window) < total,
            info=projection.info,
            security_schemes=projection.security_schemes,
        )

    # ── import ───────────────────────────────────────────────────────────────

    def _to_import_source(self, entry: CatalogEntryView) -> dict[str, str]:
        """Build a plain url IngestSource payload — never a catalog-shaped one.

        The catalog already knows the vendor and api_name from the manifest folder
        structure (``apis/openapi/{domain}/{sub}/…`` → ``extract_vendor(api_id)``),
        so we pass them through as overrides. Many catalog specs (e.g. coincap)
        omit ``x-vendor``/``contact.name`` in their ``info`` block, which would
        otherwise fail api_identifier resolution with "missing vendor" or "missing
        name". Threading the catalog vendor and api_name makes identity (and
        re-import dedup) deterministic from the catalog id rather than dependent on
        the upstream spec's info.
        """
        if not entry.spec_url:
            raise CatalogUnavailableError(f"catalog entry '{entry.api_id}' has no spec url")
        source: dict[str, str] = {"type": "url", "url": entry.spec_url, "origin": "catalog"}
        if entry.vendor:
            source["vendor"] = entry.vendor
        if entry.api_id:
            source["api_name"] = entry.api_id
        return source

    async def import_entry(self, api_id: str, identity: Identity) -> str:
        """Enqueue an async url-import for a catalog entry; return the job id."""
        entry = await self.get(api_id)
        source = self._to_import_source(entry)
        async with self._ctx.admin_db.transaction() as session:
            return await enqueue_job(
                session,
                JobKind.IMPORT,
                created_by=identity.sub,
                actor_type=identity.actor_type,
                payload={"sources": [source]},
            )

    async def ensure_imported(self, api_id: str, identity: Identity) -> str | None:
        """Hand-off seam for the Credentials PR (B6, deferred).

        Idempotently enqueue an import for ``api_id`` unless it is already
        registered locally (its ``spec_url`` already backs a non-archived
        revision — the same coverage key ``GET /catalog`` uses, not a vendor
        guess). Returns the job id when enqueued, ``None`` when the entry is
        already registered (no-op). APIs only — no workflow side effects.
        """
        entry = await self.get(api_id)
        if entry.registered:
            return None
        source = self._to_import_source(entry)
        async with self._ctx.admin_db.transaction() as session:
            return await enqueue_job(
                session,
                JobKind.IMPORT,
                created_by=identity.sub,
                actor_type=identity.actor_type,
                payload={"sources": [source]},
            )
