/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RuntimeConfig } from './RuntimeConfig';
/**
 * Update request for bearer_token credentials.
 */
export type BearerTokenUpdateRequest = {
    active?: (boolean | null);
    name?: (string | null);
    runtime_config?: (RuntimeConfig | null);
    server_variables?: (Record<string, string> | null);
    token?: (string | null);
    type: string;
};

