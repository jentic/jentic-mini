# Phase 28 Requirements — Trusted-Proxy Forwarded Identity Authentication

## Scope

Add a third human authentication path to Jentic Mini: when the request's immediate ASGI peer IP falls inside an operator-configured CIDR allowlist and a configured identity header is present, the header value is treated as an authenticated username — bypassing the bcrypt/JWT challenge. Two new env vars (`JENTIC_TRUSTED_PROXY_HEADER`, `JENTIC_TRUSTED_PROXY_NETS`) gate the path; either unset preserves today's behaviour exactly. Unknown identities are just-in-time provisioned in the `users` table with `password_hash = NULL` and `created_via = 'trusted_proxy'`; those rows can never satisfy `/user/login` or `/user/token`.

The same `JENTIC_TRUSTED_PROXY_NETS` CIDR allowlist also gates `ForwardedPrefixMiddleware`'s trust of `X-Forwarded-Prefix`, per char0n's scope-extension comment on #366 — closing the residual gap PR #369 (Phase 25) explicitly accepted pending this phase. One CIDR, two headers, no extra knobs.

## Out of Scope

- SPA UI changes — no "logged in via proxy" badge, no new pages, no `/user/me` response-shape additions. Issue #366 frames this as middleware behaviour; the SPA's existing 200-with-`logged_in: true` path is sufficient.
- Claims mapping beyond username — the header value is the username verbatim. Role mapping, group claims, multi-attribute identity, and provider-specific quirks are deferred.
- Multiple identity headers in one deployment — exactly one `JENTIC_TRUSTED_PROXY_HEADER` value.
- Admin UI for managing trusted-proxy-provisioned users — the existing user-management surface (or its absence) is unchanged.
- Schema-level CHECK constraint on `(created_via, password_hash)` consistency — logic guards in `/user/login`, `/user/token`, and the JIT path are sufficient for this phase.

## Decisions

### CIDR check uses ASGI scope peer IP only
The CIDR check resolves the peer IP from `request.client.host` (Starlette) or `scope["client"][0]` (raw ASGI middleware), never `X-Forwarded-For`. This is the entire security boundary: a malicious client cannot spoof the identity header because the only layer permitted to set it is the trusted reverse proxy, and only that proxy lives inside the CIDR. The existing `client_ip()` helper in `src/auth.py` (lines 124–131) consults `X-Forwarded-For` first and must not be reused for this gate — a new peer-only accessor is required.

### Both env vars required to activate
The trusted-proxy path activates only when *both* `JENTIC_TRUSTED_PROXY_HEADER` and `JENTIC_TRUSTED_PROXY_NETS` are non-empty. Either unset → today's behaviour (the path returns control immediately to the JWT cookie / agent key chain). This avoids a partial-config footgun and matches #366's explicit "Default (no env)" acceptance criterion.

### `ForwardedPrefixMiddleware` reuses the same CIDR
char0n's #366 comment (2026-05-11) explicitly proposes folding `X-Forwarded-Prefix` trust into the same gate. PR #369 deferred this by dropping a binary `JENTIC_TRUST_FORWARDED_PREFIX` env var in commit `10991db` to avoid an env that would be deprecated when #366 lands. This phase delivers the unified gate: one trust mechanism, two headers, no separate config surface.

### JIT user provisioning via `INSERT OR IGNORE`
Two concurrent requests from the same forwarded identity must not race on user-creation. The JIT path issues `INSERT OR IGNORE INTO users (...) VALUES (...)` followed by `SELECT` to fetch the canonical row. No new transaction primitives needed.

### `/user/login` and `/user/token` reject NULL `password_hash` with a generic 401
A JIT-provisioned account has `password_hash = NULL`. Today's login path calls `bcrypt.checkpw(password.encode(), row["password_hash"].encode())` — `None.encode()` raises `AttributeError` → 500. The new guard rejects NULL-hash rows with the same `401 {"error": "invalid_credentials"}` shape used for unknown usernames, preventing account enumeration ("this account exists but uses proxy auth").

## Constraints

- **Two-actor authentication invariant** (`specs/mission.md:45`; `specs/tech-stack.md:112`) — humans gain a third auth path, but the `X-Jentic-API-Key: tk_xxx` boundary and the agent-key codepath in `src/auth.py` (lines 418–465) must remain untouched. The new path sets `request.state.is_human_session = True` / `is_admin = True` / `toolkit_id = DEFAULT_TOOLKIT_ID`, mirroring what `_human_session_response` produces today.
- **No admin env var, no superuser bypass** (`specs/mission.md:46`) — the two new env vars must activate only the proxy-auth path; they must not create an alternate admin override. Either unset → today's behaviour, no degradation to "unauthenticated admin".
- **Alembic migrations are the schema source of truth** (`specs/mission.md:47`) — `users.created_via` and the relaxed `password_hash NOT NULL → NULLable` must arrive via a new Alembic migration with a working downgrade path. SQLite requires `batch_alter_table` (table-recreate pattern) to drop the NOT NULL constraint.
- **Broker catch-all must remain last** (`specs/mission.md:48`; `CLAUDE.md` registration order) — changes to middleware in `src/main.py` must not reorder router registration. `app.include_router(broker_router.router)` stays last.
- **Peer IP from ASGI scope only** (issue #366) — never `X-Forwarded-For`. This is the entire security boundary for both the identity header and `X-Forwarded-Prefix`.
- **Tests pass without external network** (`.claude/rules/testing.md`) — integration tests use `TestClient` with synthetic `client=(ip, port)` tuples to simulate trusted/untrusted peers.

## Context

Issue #366 frames the user need: operators running Jentic Mini behind oauth2-proxy, Google IAP, Tailscale, or any enterprise SSO already have an authenticated identity at the proxy layer. Forcing those operators to also maintain a separate bcrypt password inside Mini doubles the credential surface for the same human. The trusted-proxy header pattern is industry-standard (Grafana, Gitea, NetBox, Authelia, oauth2-proxy all support it identically) and the CIDR-gated peer-IP check is the canonical safe implementation.

This phase also closes the residual `X-Forwarded-Prefix` trust gap accepted under PR #369 (Phase 25). Commit `10991db` ("revert(config): drop JENTIC_TRUST_FORWARDED_PREFIX") explicitly deferred the gate to #366. The README deployment note at `README.md:109` is a live operator-facing warning that this phase removes.

Cross-references: `docs/auth.md` (canonical auth doc — gains a "Trusted-Proxy Forwarded Identity" subsection under Human Authentication); `README.md` (env-var table gains both vars; deferred-gap note removed); `specs/mission.md` core invariants (two-actor auth preserved, no admin env, Alembic-as-source-of-truth all hold). The Tailscale deployment pattern is already partially supported via `JENTIC_TRUSTED_SUBNETS` (`100.64.0.0/10` mention in `src/auth.py:179`); the trusted-proxy CIDR is a natural complement on the overlay-network deployment shape.

## Stakeholder Notes

- **Self-hosted SSO / reverse-proxy deployers** — primary requesters per #366. Need the SPA login screen and bcrypt challenge to drop when their proxy has already authenticated the user. Satisfied: the trusted-proxy header path treats the proxy as authoritative; JIT user provisioning eliminates manual onboarding for SSO-resolved identities.
- **Operators on the PR #369 residual-gap posture** — direct-internet exposures without a header-sanitising proxy currently face cookie-path steering and self-link prefix steering via untrusted `X-Forwarded-Prefix`. Satisfied: the same `JENTIC_TRUSTED_PROXY_NETS` allowlist now gates `X-Forwarded-Prefix`, closing the documented gap and letting the `README.md:109` warning be removed.
- **jentic-quick-claw / Tailscale users** — the overlay-network pattern (peer IP always in `100.64.0.0/10`) maps cleanly onto the new CIDR gate. No additional code; documented in `docs/auth.md` as a deployment recipe.
