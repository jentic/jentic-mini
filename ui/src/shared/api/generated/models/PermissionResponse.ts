/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single permission entry from the catalogue.
 */
export type PermissionResponse = {
    description: string;
    grantable_by_caller: boolean;
    implies: Array<string>;
    name: string;
};

