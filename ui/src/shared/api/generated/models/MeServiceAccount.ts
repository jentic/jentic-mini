/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Identity response for a service-account actor.
 */
export type MeServiceAccount = {
    approved_by?: (string | null);
    id: string;
    name: string;
    registered_by: string;
    scopes: Array<string>;
    status: string;
    token_scopes: Array<string>;
    type?: string;
};

