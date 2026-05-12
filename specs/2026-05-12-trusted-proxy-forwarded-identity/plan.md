# Phase 28 Plan — Trusted-Proxy Forwarded Identity Authentication

## Group 1 — Migration

1. Create `alembic/versions/0006_trusted_proxy_identity.py` with `revision = "0006"`, `down_revision = "0005"`, `branch_labels = None`, `depends_on = None`. Use `op.batch_alter_table("users")` for upgrade: add column `created_via TEXT DEFAULT NULL`, alter `password_hash` to `TEXT` (drop the `NOT NULL` constraint). Downgrade reverses both: drop `created_via`, restore `password_hash TEXT NOT NULL`. Follow the PRAGMA-introspect idempotence pattern from `alembic/versions/0005_agent_identity.py` so re-running upgrade is a no-op.

## Group 2 — Config

2. In `src/config.py` (after `JENTIC_PUBLIC_HOSTNAME`), add `JENTIC_TRUSTED_PROXY_HEADER = os.getenv("JENTIC_TRUSTED_PROXY_HEADER", "")` and `JENTIC_TRUSTED_PROXY_NETS = os.getenv("JENTIC_TRUSTED_PROXY_NETS", "")`. Both default to empty string (feature inactive).

## Group 3 — Auth.py trusted-proxy path

3. In `src/auth.py` (near `trusted_subnets()` / `is_trusted_ip()` at lines 166–216) add `trusted_proxy_nets() -> list[str]` parsing `JENTIC_TRUSTED_PROXY_NETS` (comma-split, strip) and `is_proxy_trusted_peer(peer_ip: str) -> bool` performing CIDR membership using the already-imported `ipaddress` module.

4. In `src/auth.py` add `async def _trusted_proxy_response(request, call_next) -> Response | None`. Returns `None` immediately when either `JENTIC_TRUSTED_PROXY_HEADER` or `JENTIC_TRUSTED_PROXY_NETS` is empty (feature inactive). Reads peer IP from `request.client.host` (never `X-Forwarded-For`). On untrusted peer + header present, log `logger.warning("PROXY_AUTH untrusted_peer=%s header=%s ignored", peer_ip, JENTIC_TRUSTED_PROXY_HEADER)` and return `None` so the next auth path runs. On trusted peer + header present, JIT-provision the user via `INSERT OR IGNORE INTO users (id, username, password_hash, created_via) VALUES (?, ?, NULL, 'trusted_proxy')` then `SELECT` to fetch the canonical row, set `request.state.is_human_session = True`, `request.state.is_admin = True`, `request.state.toolkit_id = DEFAULT_TOOLKIT_ID`, and return `await call_next(request)`. On trusted peer + no header, return `None`.

5. In `APIKeyMiddleware.dispatch` (`src/auth.py:327–507`), slot a call to `_trusted_proxy_response(request, call_next)` immediately after the `_human_session_response` block (~line 414) and before the agent-key block (~line 418). Order: JWT cookie → trusted-proxy header → agent key → reject.

## Group 4 — ForwardedPrefixMiddleware CIDR gate

6. In `src/main.py`, import `JENTIC_TRUSTED_PROXY_NETS` from `src.config` and `is_proxy_trusted_peer` from `src.auth`. Do not reorder existing imports.

7. Modify `ForwardedPrefixMiddleware.__call__` (`src/main.py:114–129`) to extract `peer_ip = scope.get("client", ("", 0))[0]` and skip the `X-Forwarded-Prefix` header read when `JENTIC_TRUSTED_PROXY_NETS` is set but the peer fails the CIDR check; emit `logger.warning("FORWARDED_PREFIX untrusted_peer=%s ignored", peer_ip)`. When `JENTIC_TRUSTED_PROXY_NETS` is unset, preserve today's unconditional-trust behaviour so operators on existing configs do not break.

8. Update the `ForwardedPrefixMiddleware` docstring (`src/main.py:96–108`) to remove the stale "future peer-IP-gated trust boundary" language and document the live gate.

## Group 5 — Login null-hash guard

9. In `src/routers/user.py` login handler (~line 192), add `if not row or row["password_hash"] is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode())` and return `401 {"error": "invalid_credentials"}` — same shape regardless of which sub-condition fired (no enumeration leak).

10. Apply the identical guard in the `/user/token` OAuth2 password-grant handler (~line 276).

11. In `POST /user/create` (`src/routers/user.py:103`), set `created_via = 'local'` on the INSERT so the root account is unambiguously distinct from JIT proxy rows.

## Group 6 — Tests, docs, lifecycle

12. Create `tests/test_trusted_proxy_auth.py` covering the six #366 acceptance criteria plus prefix-gating: (a) no-env passthrough; (b) trusted peer + header → 200 + identity + JIT row created with `password_hash IS NULL` and `created_via='trusted_proxy'`; (c) trusted peer + no header → 401; (d) untrusted peer + header → 401 + WARN log on `jentic.auth`; (e) trusted peer + spoofed `X-Forwarded-For` outside CIDR → still authenticated (peer IP is the gate); (f) JIT-provisioned account at `/user/login` and `/user/token` → 401 with `invalid_credentials`; (g) trusted peer + `X-Forwarded-Prefix: /foo` → `root_path` applied; (h) untrusted peer + same prefix header → `root_path` stays unset + WARN log. Use `TestClient(app, client=(ip, port))` to fake peer addresses; `monkeypatch.setenv` to toggle env vars.

13. Update `docs/auth.md`: add a "Trusted-Proxy Forwarded Identity" subsection under Human Authentication describing the env vars, the CIDR-gate security boundary, JIT provisioning, and the NULL-hash login rejection. Update the `users` schema documentation in "Database tables" to show `created_via` and NULLable `password_hash`.

14. Update `README.md`: add `JENTIC_TRUSTED_PROXY_HEADER` and `JENTIC_TRUSTED_PROXY_NETS` rows to the env-var configuration table. Remove the `> **Deployment note...` paragraph at line 109 that references issue #366 as a future fix.

15. Append ` ✅` (one space then U+2705) to the `## Phase 28 — Trusted-Proxy Forwarded Identity Authentication` heading in `specs/roadmap.md`. Leave the rest of the phase block unchanged.

## Group 7 — Verify

16. `pdm run test tests/test_trusted_proxy_auth.py -v` exits 0; all listed test functions pass.

17. `pdm run test` exits 0; no regression in `tests/test_auth_boundary.py`, `tests/test_root_path.py`, `tests/test_auth_boundary_comprehensive.py`, or the wider suite.

18. `pdm run lint` exits 0.

19. `PYTHONPATH=. pdm run python -m alembic upgrade head` exits 0; `PYTHONPATH=. pdm run python -m alembic downgrade -1` exits 0; second `PYTHONPATH=. pdm run python -m alembic upgrade head` exits 0.

20. After upgrade, `PYTHONPATH=. pdm run python -c "import sqlite3, os; db = sqlite3.connect(os.environ['DB_PATH']); cols = {r[1]: r[3] for r in db.execute('PRAGMA table_info(users)')}; assert 'created_via' in cols and cols['password_hash'] == 0; print('schema ok')"` exits 0 and prints `schema ok`.

21. `grep -F "JENTIC_TRUSTED_PROXY_HEADER" README.md` exits 0; `grep -F "JENTIC_TRUSTED_PROXY_NETS" README.md` exits 0.

22. `grep -F "#366" README.md` exits 1 (deferred-gap note is gone).

23. `grep -F "JENTIC_TRUSTED_PROXY_HEADER" docs/auth.md` exits 0; `grep -F "created_via" docs/auth.md` exits 0.

24. `grep -F "future peer-IP-gated" src/main.py` exits 1 (stale docstring updated).

25. `grep -F "## Phase 28 — Trusted-Proxy Forwarded Identity Authentication ✅" specs/roadmap.md` exits 0 (single space before U+2705 is load-bearing per the lifecycle rule).
