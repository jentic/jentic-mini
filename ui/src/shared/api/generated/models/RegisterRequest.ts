/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /register request body.
 */
export type RegisterRequest = {
    client_name: string;
    grant_types?: (Array<string> | null);
    jwks: Record<string, any>;
    scope?: (string | null);
    token_endpoint_auth_method?: (string | null);
};

