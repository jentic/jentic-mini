/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PermissionRule } from './PermissionRule';
/**
 * Body for POST /toolkits/{id}/access-requests.
 *
 * **`type=grant`** — bind an upstream API credential to this toolkit:
 * ```json
 * {
     * "type": "grant",
     * "credential_id": "api.elevenlabs.io",
     * "rules": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}],
     * "reason": "I need to generate audio"
     * }
     * ```
     *
     * **`type=modify_permissions`** — update rules on a credential already bound to this toolkit:
     * ```json
     * {
         * "type": "modify_permissions",
         * "credential_id": "api.elevenlabs.io",
         * "rules": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}],
         * "reason": "I need write access to TTS only"
         * }
         * ```
         */
        export type AccessRequestBody = {
            /**
             * `grant` — bind an upstream API credential to this toolkit. Requires `credential_id`; `rules` is optional (defaults to system safety rules only). `modify_permissions` — update permission rules on a credential already bound to this toolkit. Requires both `credential_id` and `rules`.
             */
            type: AccessRequestBody.type;
            /**
             * The upstream API credential to act on. Discover available IDs and labels via `GET /credentials` or `GET /credentials?api_id=<host>`.
             */
            credential_id: string;
            /**
             * Ordered list of permission rules. For `grant`, applied atomically when approved. For `modify_permissions`, replaces the current agent rules entirely. System safety rules (deny writes, deny sensitive paths) are always appended after these and cannot be removed.
             *
             * Each `PermissionRule` object — all fields except `effect` are optional and AND-combined:
             * - `effect` *(required)*: `"allow"` or `"deny"`
             * - `methods`: list of HTTP verbs to match, e.g. `["GET", "POST"]` — omit to match all
             * - `path`: Python regex matched against the **path component only** of the upstream URL (host and query string are excluded). Uses `re.search()` — **substring match by default**, case-insensitive. Use `^`/`$` to anchor. `|` is regex OR.
             * - Unanchored: `"issues"` matches any path *containing* the word — often too broad
             * - Prefix: `"^/repos/myorg/myrepo/"` — everything under that path
             * - Exact: `"^/v1/voices$"` — only that specific endpoint
             * - **Tip:** always anchor with `^` when generating allow rules to avoid unintended matches
             * - `operations`: list of regexes matched against the operation ID
             *
             * **Examples:**
             * ```json
             * [{"effect": "allow", "methods": ["POST"], "path": "^/v1/text-to-speech$"}]
             * [{"effect": "deny",  "path": "admin|billing|pay"}]
             * [{"effect": "allow", "operations": ["^get_voices$", "^tts"]}]
             * ```
             */
            rules?: Array<PermissionRule>;
            /**
             * Optional. Shown in the human approval UI. Usually inferred automatically from the credential.
             */
            api_id?: (string | null);
            /**
             * Explain to the human why access is needed. Shown in the approval UI.
             */
            reason?: (string | null);
        };
        export namespace AccessRequestBody {
            /**
             * `grant` — bind an upstream API credential to this toolkit. Requires `credential_id`; `rules` is optional (defaults to system safety rules only). `modify_permissions` — update permission rules on a credential already bound to this toolkit. Requires both `credential_id` and `rules`.
             */
            export enum type {
                GRANT = 'grant',
                MODIFY_PERMISSIONS = 'modify_permissions',
            }
        }

