# Decisions

Architectural decisions that deserve a written record. Each entry names the
context, the choice made, and the implications for future work.

## `auth_type` is the live credential scheme column (raised 2026-03-21, revised 2026-05-04)

**Context:** Credentials are written with `auth_type` (one of `bearer`, `basic`,
`apiKey`, `none`). The Pipedream broker path additionally writes the reserved
internal value `pipedream_oauth` to the same column (see
`src/brokers/pipedream.py`); agents cannot set `pipedream_oauth` via
`POST /credentials` — it is enforced as reserved by `src/routers/credentials.py`.

An earlier version of this note referred to a `scheme_name` column. That column
was retired by migration `0004_credential_routes`: `scheme_name` now survives
only as a legacy parameter name in `src/vault.py` (`create_credential(...,
scheme_name=...)`), which is immediately stored as `auth_type`. The Python
parameter is a misnomer — the persisted column is `auth_type`.

**Decision:** Treat `auth_type` as the canonical credential scheme column. Do
not add new code that reads or writes a `scheme_name` column.

**Future plan — multi-scheme disambiguation:** If a single API exposes multiple
security schemes of the same `auth_type` (e.g. two distinct apiKey header names),
matching on `auth_type` alone is not enough. The planned resolution is to match
on the security-scheme `type` as defined by OpenAPI (`bearer`, `basic`,
`apiKey`, `oauth2`, `openIdConnect`) combined with scheme-specific disambiguators
already carried on the credential (e.g. `identity`, `scheme.name`). A new column
is not currently needed; the `auth_type` enum in `src/models.py` already mirrors
the OpenAPI type space minus the variants that have no in-scope use case.

**Not planned:** Renaming `auth_type` → `scheme_type`, or adding `scheme_name`
back as a second column. Both would be migration churn without a concrete
use case.
