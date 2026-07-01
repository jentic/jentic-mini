/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Permission rule response (includes system fields).
 */
export type PermissionRuleReadSchema = {
    _comment?: (string | null);
    _system?: boolean;
    effect: PermissionRuleReadSchema.effect;
    methods?: (Array<string> | null);
    operations?: (Array<string> | null);
    path?: (string | null);
};
export namespace PermissionRuleReadSchema {
    export enum effect {
        ALLOW = 'allow',
        DENY = 'deny',
    }
}

