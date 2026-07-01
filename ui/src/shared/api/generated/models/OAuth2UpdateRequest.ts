/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RuntimeConfig } from './RuntimeConfig';
/**
 * Update request for oauth2 credentials.
 */
export type OAuth2UpdateRequest = {
    active?: (boolean | null);
    client_secret?: (string | null);
    name?: (string | null);
    runtime_config?: (RuntimeConfig | null);
    scopes?: (Array<string> | null);
    server_variables?: (Record<string, string> | null);
    token_url?: (string | null);
    type: string;
};

