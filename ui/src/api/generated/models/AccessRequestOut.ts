/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * An access request filed by an agent and awaiting human approval.
 *
 * The `payload` shape depends on `type`:
 *
 * **`grant`** — bind a new upstream credential to this toolkit (optionally with rules):
 * ```json
 * { "type": "grant", "payload": { "credential_id": "api.github.com", "rules": [...] }, "reason": "..." }
 * ```
 *
 * **`modify_permissions`** — update permission rules on an already-bound credential:
 * ```json
 * { "type": "modify_permissions", "payload": { "credential_id": "api.github.com", "rules": [...] }, "reason": "..." }
 * ```
 */
export type AccessRequestOut = Record<string, any>;
