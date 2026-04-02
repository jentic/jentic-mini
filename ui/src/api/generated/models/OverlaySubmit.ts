/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type OverlaySubmit = {
    /**
     * Full OpenAPI Overlay 1.0 document as a JSON object. Use this to patch the stored spec for any API — security schemes, base URL corrections, operation metadata, extra extensions, etc.
     *
     * **Structure:**
     * ```json
     * {
         * "overlay": "1.0.0",
         * "info": {"title": "<description>", "version": "1.0.0"},
         * "actions": [
             * {
                 * "target": "<JSONPath expression>",
                 * "update": { }
                 * }
                 * ]
                 * }
                 * ```
                 *
                 * **Common targets:**
                 * - `"$"` — root of the spec (components, info, servers)
                 * - `"$.paths[*][*]"` — all operations (apply global security)
                 * - `"$.paths./foo.get"` — a specific operation
                 *
                 * **Security scheme example** (adding BearerAuth to an API):
                 * ```json
                 * {
                     * "overlay": "1.0.0",
                     * "info": {"title": "GitHub REST auth", "version": "1.0.0"},
                     * "actions": [
                         * {
                             * "target": "$",
                             * "update": {
                                 * "components": {
                                     * "securitySchemes": {
                                         * "BearerAuth": {"type": "http", "scheme": "bearer"}
                                         * }
                                         * }
                                         * }
                                         * },
                                         * {
                                             * "target": "$.paths[*][*]",
                                             * "update": {"security": [{"BearerAuth": []}]}
                                             * }
                                             * ]
                                             * }
                                             * ```
                                             *
                                             * **Compound apiKey schemes** (e.g. Discourse — two separate apiKey headers): name one scheme `Secret` (the primary key) and one `Identity` (the username/ID). The broker resolves these by canonical name without needing further annotation.
                                             */
                                            overlay: Record<string, any>;
                                            contributed_by?: (string | null);
                                        };

