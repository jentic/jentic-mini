/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single OAuth2 flow within a security scheme.
 */
export type SecuritySchemeFlowResponse = {
    authorization_url?: (string | null);
    flow_type: string;
    refresh_url?: (string | null);
    scopes?: (Record<string, string> | null);
    token_url?: (string | null);
};

