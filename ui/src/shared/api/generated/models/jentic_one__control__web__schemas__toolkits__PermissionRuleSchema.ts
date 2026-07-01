/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Permission rule for a toolkit-credential binding.
 *
 * Rules are evaluated first-match-wins. If no rule matches, the request is
 * denied (default-deny). A binding with zero rules therefore blocks all
 * operations — users must explicitly add at least one allow rule.
 */
export type jentic_one__control__web__schemas__toolkits__PermissionRuleSchema = {
    /**
     * Whether this rule allows or denies the matched request.
     */
    effect: jentic_one__control__web__schemas__toolkits__PermissionRuleSchema.effect;
    /**
     * HTTP methods to match (case-insensitive). None matches all.
     */
    methods?: (Array<string> | null);
    /**
     * OpenAPI operation IDs to match. None matches all operations.
     */
    operations?: (Array<string> | null);
    /**
     * Regex pattern for the request path. None matches all paths.
     */
    path?: (string | null);
};
export namespace jentic_one__control__web__schemas__toolkits__PermissionRuleSchema {
    /**
     * Whether this rule allows or denies the matched request.
     */
    export enum effect {
        ALLOW = 'allow',
        DENY = 'deny',
    }
}

