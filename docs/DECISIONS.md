
---

## scheme_name → future scheme_type (raised 2026-03-21)

**Context:** All credentials in the default toolkit have `scheme_name: null`. The Pipedream broker path is the only active user of `scheme_name` (hardcoded to `'pipedream_oauth'`). No regular credentials use the field.

**Decision:** Leave `scheme_name` in place for now (no active users, so no breakage from leaving it). Do NOT rely on it for new credential matching.

**Future plan:** When multi-scheme API disambiguation is needed, rename the field to **`scheme_type`** — not `scheme_name` — because the valid values are a finite, spec-defined set:

- `bearer`
- `basic`  
- `apiKey`
- `oauth2_client_credentials`
- `openIdConnect`

These map to the `type` field on `SchemeInput`. The key distinction: `scheme_name` was meant to match the *key name* in `securitySchemes` (e.g. `"BasicAuth"`, `"bearerAuth"` — arbitrary strings set by the spec author). `scheme_type` would instead match the *type* (standardised values from the OpenAPI spec). This is more robust and less brittle to naming convention differences between API specs.

**Also needed:** Document the valid values in the API OpenAPI spec when the field is promoted to `scheme_type`.

