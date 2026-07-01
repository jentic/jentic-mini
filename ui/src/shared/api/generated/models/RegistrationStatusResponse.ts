/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /register/{agent_id} response.
 */
export type RegistrationStatusResponse = {
    client_id: string;
    grant_types?: Array<string>;
    status: string;
    token_endpoint_auth_method?: string;
};

