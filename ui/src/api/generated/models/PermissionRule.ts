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
 * **`path`** — Python regex matched against the **path component only** of the upstream
 * request URL. The host and query string are never included. Matching uses `re.search()`
 * (Python), which means:
 *
 * - It is always a **regex** — not a glob, not a prefix string.
 * - It is **case-insensitive**.
 * - It is a **substring match by default** — the pattern can match anywhere in the path
 * unless you anchor it with `^` and/or `$`.
 * - `|` is regex OR (matches either side).
 *
 * **Anchoring guide:**
 *
 * | Intent | Pattern | Matches | Does NOT match |
 * |--------|---------|---------|----------------|
 * | Substring (any path containing word) | `"issues"` | `/repos/x/issues`, `/v1/issues/7` | (nothing — too broad for deny rules) |
 * | Prefix (everything under a path) | `"^/repos/jentic/jentic-mini/"` | `/repos/jentic/jentic-mini/issues/34` | `/repos/other/repo/issues` |
 * | Exact endpoint | `"^/v1/voices$"` | `/v1/voices` | `/v1/voices/123` |
 * | One endpoint + subresources | `"^/repos/jentic/jentic-mini/issues/[0-9]+/comments$"` | `/repos/jentic/jentic-mini/issues/34/comments` | `/repos/jentic/jentic-mini/issues` |
 * | Block any sensitive word | `"admin\|billing\|pay"` | `/v1/admin/users`, `/billing/invoice` | n/a |
 *
 * **Tip for agents generating rules:** always anchor with `^` to avoid unintentionally
 * matching longer paths, and use `$` to prevent prefix over-permission. An unanchored
 * pattern like `"comments"` would also match `/v1/my-comments-service/admin`.
 *
 * **`operations`** — list of regexes matched against the operation ID via `re.search()`.
 * E.g. `["tts", "speech"]` matches any operation whose ID contains "tts" or "speech".
 *
 * System safety rules (always active, cannot be removed) are marked `_system: true` in
 * `GET .../permissions` responses (see `PermissionRuleOut`). They deny sensitive paths
 * and write methods by default. The `_system` and `_comment` fields are response-only
 * and will be rejected in request bodies.
 *
 * **Examples:**
 * ```json
 * {"effect": "allow", "methods": ["POST"], "path": "^/v1/text-to-speech$"}
 * {"effect": "allow", "methods": ["POST"], "path": "^/repos/jentic/jentic-mini/issues/[0-9]+/comments$"}
 * {"effect": "allow", "methods": ["GET", "POST"], "path": "^/repos/jentic/jentic-mini/"}
 * {"effect": "deny",  "path": "admin|billing|pay"}
 * {"effect": "allow", "operations": ["^github_get_repo$"]}
 * ```
 */
export type PermissionRule = {
    /**
     * `"allow"` or `"deny"`
     */
    effect: PermissionRule.effect;
    /**
     * HTTP methods to match, e.g. `["GET", "POST"]`. Omit to match all methods.
     */
    methods?: (Array<string> | null);
    /**
     * Python regex matched with `re.search()` against the **path component only** of the upstream URL (no host, no query string). Matching is case-insensitive and substring by default — use `^`/`$` to anchor. `|` is regex OR. Example: `"^/repos/jentic/jentic-mini/issues/[0-9]+/comments$"` matches only that exact endpoint; omitting anchors would also match any path containing that substring.
     */
    path?: (string | null);
    /**
     * List of regexes matched against the operation ID. E.g. `["tts", "speech"]`.
     */
    operations?: (Array<string> | null);
};
export namespace PermissionRule {
    /**
     * `"allow"` or `"deny"`
     */
    export enum effect {
        ALLOW = 'allow',
        DENY = 'deny',
    }
}

