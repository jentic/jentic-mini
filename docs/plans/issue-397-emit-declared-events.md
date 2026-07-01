> Issue: jentic/jentic-one#397

## Context

`EventType` (`src/jentic_one/shared/models/events.py`) declares 11 namespaced
event types, but three are never emitted by any code in `src/` and are documented
as **(planned)** in `docs/development/events.md` (rows 34–36):
`execution.repeated_failure`, `credential.expiring_soon`, and `credential.expired`.
As a consequence the events feed today only ever produces `info` and `error`
severities — `EventSeverity.WARNING` is unreachable and `EventSeverity.CRITICAL`
is unused by any emitter.

The Agent Rail UI (tracked in `jentic-one-ui-migration`) already ships filter
chips for the `creds`/`other` kinds and the `warning`/`critical` severities, plus
an "audio on critical" cue — all currently dead affordances. This plan wires the
backend emitters so those affordances become live, and makes a deliberate call on
which event (if any) carries `CRITICAL`.

The work has three independent emitters plus shared plumbing:

1. **`credential.expiring_soon` / `credential.expired`** — a scheduled sweep over
   stored OAuth token expiries (`oauth_tokens.expires_at` lives in the **control**
   DB; events are written to the **admin** DB). `expiring_soon` ⇒ `warning`,
   `expired` ⇒ `error`. Dedup must be persistent and idempotent (a token sits in
   the "expiring" state for the whole warning window and across worker restarts),
   so this needs a marker on the token row rather than the in-memory dedup used by
   the circuit/auth-failure emitters.
2. **`execution.repeated_failure`** — detected from the execution lifecycle when an
   actor's failures for a given toolkit+operation cross a threshold within a rolling
   window. Both the async worker path (`execution_handler.py`) and the sync/streaming
   broker path (`broker/services/execution/service.py`) emit `execution.failed`, so
   detection lives in a shared helper both call. `ExecutionRecord` rows are in the
   **admin** DB alongside `events`, so detection is a single-DB query.
3. **Severity decision** — recommendation: `execution.repeated_failure` emits
   `ERROR` normally and escalates to `CRITICAL` past a second, higher threshold.
   This makes `warning` (expiring_soon), `error`, and `critical` all reachable,
   so the rail's full chip set and the critical-audio cue all fire on real events.

All `emit_event(...)` calls are best-effort and wrapped in `try/except` that logs
`emit_event_failed` — the new emitters must follow that same convention so a feed
write never breaks the operation it observes.

## Files to Change

1. `src/jentic_one/shared/config.py` — extend `SecurityConfig` with the new tunables:
   `credential_expiring_soon_window_h`, `credential_expiry_sweep_interval_ticks`,
   `execution_repeated_failure_threshold`, `execution_repeated_failure_window_s`,
   `execution_repeated_failure_critical_threshold`.
2. `src/jentic_one/migrations/control/versions/<rev>_add_oauth_token_expiry_event_markers.py` —
   new Alembic migration adding nullable `expiring_soon_event_at` and
   `expired_event_at` timestamp columns to `oauth_tokens` (persistent at-most-once dedup).
3. `src/jentic_one/control/core/schema/oauth_tokens.py` — add the two marker columns
   to the `OAuthToken` ORM model.
4. `src/jentic_one/control/repos/oauth_token_repo.py` — add
   `list_expiry_candidates(...)` (select tokens not revoked, with `expires_at` set,
   that are newly-expired or newly-in-window and whose corresponding marker is null,
   with `SKIP LOCKED`) and a `mark_expiry_event_emitted(...)` stamper.
5. `src/jentic_one/shared/events/repeated_failure.py` — new shared helper
   `maybe_emit_repeated_failure(session, *, actor_id, actor_type, toolkit_id, operation_id, trace_id, config)`:
   counts recent failed `ExecutionRecord`s for the key within the window, checks for an
   existing un-superseded `execution.repeated_failure` event, and emits ERROR/CRITICAL.
6. `src/jentic_one/shared/jobs/credential_expiry_scanner.py` — new background sweeper
   (`CredentialExpiryScanner`) modelled on `WorkerLoop.run()`: tick loop that reads
   expiry candidates from control DB and emits `credential.expiring_soon`/`credential.expired`
   into admin DB, stamping the markers in the same control-DB transaction.
7. `src/jentic_one/shared/web/app_factory.py` — start/drain the `CredentialExpiryScanner`
   in the worker lifespan when both `control` and `admin` DBs are present (mirror
   `_start_worker`/`_stop_worker`).
8. `src/jentic_one/shared/jobs/execution_handler.py` — call `maybe_emit_repeated_failure`
   in `_emit_lifecycle` on the `FAILED` branch.
9. `src/jentic_one/broker/services/execution/service.py` — call `maybe_emit_repeated_failure`
   in `_emit_execution_lifecycle` on the `FAILED` branch (needs `toolkit_id`/`operation_id`
   threaded in; confirm they're in scope at the call site).
10. `docs/development/events.md` — update rows 34–36 from **(planned)** to their real
    sources/severities, add the new config knobs, and add dedup/throttle rows for the
    three new events.
11. `tests/unit/shared/test_repeated_failure.py` — new: threshold, window expiry,
    dedup/at-most-once, and ERROR→CRITICAL escalation.
12. `tests/unit/shared/test_credential_expiry_scanner.py` — new: emits each event once,
    re-sweep is a no-op (marker dedup), warning vs error severity, skips revoked tokens.
13. `tests/integration/admin/test_events_emission.py` and a control-DB integration test —
    extend to cover the real DB round-trip for the three new event types.

## Build Order

1. **Config knobs** — extend `SecurityConfig`.
   1.1. Add the five fields to `SecurityConfig` with `Field(...)` constraints, matching
        the existing `auth_failure_event_threshold` style: window/interval/threshold ints
        with `ge=1`. Sensible defaults: `credential_expiring_soon_window_h=72`,
        `credential_expiry_sweep_interval_ticks=60`, `execution_repeated_failure_threshold=5`,
        `execution_repeated_failure_window_s=300`,
        `execution_repeated_failure_critical_threshold=20`.
   1.2. Verify: `uv run python -c "from jentic_one.shared.config import SecurityConfig; print(SecurityConfig())"`
        prints the new defaults; existing config-parsing unit tests still pass.

2. **OAuth-token expiry markers (schema + migration + repo).**
   2.1. Add `expiring_soon_event_at: Mapped[datetime | None]` and
        `expired_event_at: Mapped[datetime | None]` (both `UTCDateTime(), nullable=True`)
        to `OAuthToken`.
   2.2. Generate the control-DB migration (follow `docs/rules/` migration guide; revision
        id consistent with existing `*_add_*` filenames). Upgrade adds both nullable columns;
        downgrade drops them.
   2.3. Add `OAuthTokenRepository.list_expiry_candidates(session, *, now, window_start, limit)`:
        select rows where `revoked_at IS NULL` and `expires_at IS NOT NULL` and either
        (`expires_at <= now` and `expired_event_at IS NULL`) or
        (`expires_at <= window_end` and `expires_at > now` and `expiring_soon_event_at IS NULL`),
        with `.with_for_update(skip_locked=True)` for multi-replica safety. Add
        `mark_expiry_event_emitted(session, token, *, kind, at)` to stamp the right column.
   2.4. Verify: a unit/integration test inserts tokens at varying `expires_at` and asserts the
        candidate query selects exactly the rows in each state and skips revoked/already-marked rows.

3. **Repeated-failure detection helper.**
   3.1. Create `shared/events/repeated_failure.py` with
        `maybe_emit_repeated_failure(...)`. Count `ExecutionRecord`s where
        `status == "failed"`, `actor_id == actor_id`, `toolkit_id == toolkit_id`,
        `operation_id == operation_id`, `started_at >= now - window_s`. If
        `count >= threshold`: choose severity (`CRITICAL` when
        `count >= critical_threshold`, else `ERROR`), then dedup by checking for an existing
        `execution.repeated_failure` event for the same key (match on `data` fields) within the
        same window — emit only if none exists. Put the counting/dedup window in `data`
        (`{"actor_id","toolkit_id","operation_id","failure_count","window_s"}`).
   3.2. Wrap the emit in `try/except` logging `emit_event_failed`, consistent with existing emitters.
   3.3. Verify: `tests/unit/shared/test_repeated_failure.py` — below threshold (no event),
        at threshold (one ERROR), repeated calls within window (still one — dedup),
        at/over critical threshold (CRITICAL), and window roll-off (new event after window).

4. **Wire repeated-failure into both execution emit paths.**
   4.1. In `execution_handler.py:_emit_lifecycle`, on the `else`/FAILED branch (after the
        `EXECUTION_FAILED` emit), call `maybe_emit_repeated_failure` with the same session and
        the execution's `actor_id`/`toolkit_id`/`operation_id`/`trace_id` and `config`. Thread
        `config`/needed identifiers into the handler if not already present.
   4.2. In `broker/services/execution/service.py:_emit_execution_lifecycle`, add the same call on
        the FAILED branch; confirm `toolkit_id`/`operation_id` are available at the call site
        (thread them through if not).
   4.3. Verify: existing `tests/unit/shared/test_execution_handler.py` still passes; add a case
        asserting `execution.repeated_failure` fires once after N failures in both paths.

5. **Credential-expiry scanner (background sweep + lifespan wiring).**
   5.1. Create `shared/jobs/credential_expiry_scanner.py` with `CredentialExpiryScanner`
        holding `control_db` + `admin_db` (or the `Context`) and a `run()`/tick loop modelled on
        `WorkerLoop.run()` (catch-and-log non-cancellation errors; sweep every
        `credential_expiry_sweep_interval_ticks`). Each tick: read candidates from control DB,
        and per token, in one transaction emit the event into admin DB and stamp the marker in
        control DB. Use `expiring_soon` ⇒ WARNING and `expired` ⇒ ERROR (`requires_action=True`
        on `expired`). Carry only non-secret identifiers in `data` (`credential_id`, `expires_at`,
        `api_vendor`) — never token material, mirroring `emit_credential_access`.
   5.2. In `app_factory.py`, start the scanner task alongside the worker when
        `ctx.has_db("control") and ctx.has_db("admin")`, and drain/cancel it in the teardown path
        (mirror `_start_worker`/`_stop_worker`).
   5.3. Verify: `tests/unit/shared/test_credential_expiry_scanner.py` — one event per token per
        state, second sweep is a no-op (marker dedup), correct severities, revoked tokens skipped.

6. **Docs + severity decision.**
   6.1. Update `docs/development/events.md` rows 34–36: `EXECUTION_REPEATED_FAILURE` →
        ExecutionHandler/BrokerService (error, critical past `*_critical_threshold`);
        `CREDENTIAL_EXPIRING_SOON` → CredentialExpiryScanner (warning);
        `CREDENTIAL_EXPIRED` → CredentialExpiryScanner (error). Add the new `security.*` config
        knobs and add Deduplication/Throttling rows for all three (marker-column dedup for
        credential events; per-key window dedup for repeated_failure).
   6.2. Record the severity decision in the doc: `CRITICAL` is now reserved for and emitted by
        `execution.repeated_failure` past the critical threshold, so the rail's critical-audio
        cue stays. Note this back on the UI side (`jentic-one-ui-migration` API-CONTRACT) so the
        chips/cue are confirmed live rather than no-ops.
   6.3. Verify: `make score` (OpenAPI unaffected — no new routes) and a docs read-through;
        confirm the conformance test (`tests/unit/admin/test_events_conformance.py`) still passes
        (all types already in `EventType.ALL`).

## Verification

1. **Lint/type/tests:** `make check` passes (ruff + mypy strict + unit + arch).
2. **Migration round-trips:** apply the new control migration up then down against a fixtures DB
   (`make start-fixtures` then the project migration CLI) — `oauth_tokens` gains/loses both marker
   columns cleanly with no data loss on existing rows.
3. **Repeated-failure unit suite** (`tests/unit/shared/test_repeated_failure.py`): below-threshold
   emits nothing; the Nth failure within the window emits exactly one `execution.repeated_failure`
   (ERROR); further failures in the window emit none (dedup); crossing the critical threshold emits
   `CRITICAL`; a failure after the window emits a fresh event. Both the async-worker and sync-broker
   paths trigger it.
4. **Credential-scanner unit suite** (`tests/unit/shared/test_credential_expiry_scanner.py`):
   a token within the warning window emits one `credential.expiring_soon` (WARNING) and stamps
   `expiring_soon_event_at`; an expired token emits one `credential.expired` (ERROR,
   `requires_action=True`) and stamps `expired_event_at`; a second sweep over the same tokens emits
   nothing; revoked tokens are skipped.
5. **Integration round-trip:** with fixtures running, drive the scanner and a repeated-failure
   scenario against real DBs; `GET /events?severity=warning`, `?severity=critical`, and
   `?event_type=credential.expired` each return the newly-emitted rows with correct `_links`,
   confirming the cross-DB (control→admin) write path and the API filters work end-to-end.
6. **Severity coverage:** query the feed after exercising all emitters and confirm every
   `EventSeverity` value (`info`, `warning`, `error`, `critical`) is now produced by at least one
   real emitter — closing the gap called out in the issue.
