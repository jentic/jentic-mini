/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /register 201 response.
 */
export type RegisterResponse = {
    client_id: string;
    grant_types?: Array<string>;
    registration_access_token: string;
    registration_client_uri: string;
    status: string;
    token_endpoint_auth_method?: string;
};

