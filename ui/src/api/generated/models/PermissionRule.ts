/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single access control rule. All fields are optional; conditions are AND-combined.
 * First matching rule wins. Agent rules are evaluated before system safety rules.
 *
 * **`effect`** — `"allow"` or `"deny"` (required)
 *
 * **`methods`** — list of HTTP methods to match, e.g. `["GET", "POST"]`.
 * Omit to match all methods.
 *
 * **`path`** — Python regex matched with `re.search()` against the upstream request path.
 * This is a **substring match** — `"admin|pay"` matches any path *containing* those words.
 * Case-insensitive. Use `^`/`$` to anchor. `|` is regex OR.
 *
 * Examples:
 * - `"admin|billing|pay"` — matches `/v1/admin/users`, `/billing/invoice`, `/pay`
 * - `"^/v1/voices$"` — matches only exactly `/v1/voices`
 * - `"text-to-speech"` — matches any path containing that substring
 *
 * **`operations`** — list of regexes matched against the operation ID via `re.search()`.
 * E.g. `["tts", "speech"]` matches any operation whose ID contains "tts" or "speech".
 *
 * System safety rules (always active, cannot be removed) are marked `_system: true` in
 * `GET .../permissions` responses. They deny sensitive paths and write methods by default.
 *
 * **Examples:**
 * ```json
 * {"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}
 * {"effect": "deny",  "path": "admin|billing|pay"}
 * {"effect": "allow", "operations": ["^github_get_repo$"]}
 * ```
 */
export type PermissionRule = Record<string, any>;
