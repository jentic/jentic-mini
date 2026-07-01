/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RuntimeConfig } from './RuntimeConfig';
/**
 * Update request for basic credentials.
 */
export type BasicAuthUpdateRequest = {
    active?: (boolean | null);
    name?: (string | null);
    password?: (string | null);
    runtime_config?: (RuntimeConfig | null);
    server_variables?: (Record<string, string> | null);
    type: string;
    username?: (string | null);
};

