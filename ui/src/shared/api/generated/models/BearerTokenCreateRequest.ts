/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { APIReferenceRequest } from './APIReferenceRequest';
import type { RuntimeConfig } from './RuntimeConfig';
/**
 * Create request for bearer_token credentials.
 */
export type BearerTokenCreateRequest = {
    api: APIReferenceRequest;
    name: string;
    provider?: string;
    runtime_config?: (RuntimeConfig | null);
    server_variables?: (Record<string, string> | null);
    token: string;
    type: string;
};

