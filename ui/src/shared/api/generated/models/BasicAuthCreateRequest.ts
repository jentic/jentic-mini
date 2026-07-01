/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { APIReferenceRequest } from './APIReferenceRequest';
import type { RuntimeConfig } from './RuntimeConfig';
/**
 * Create request for basic credentials.
 */
export type BasicAuthCreateRequest = {
    api: APIReferenceRequest;
    name: string;
    password: string;
    provider?: string;
    runtime_config?: (RuntimeConfig | null);
    server_variables?: (Record<string, string> | null);
    type: string;
    username: string;
};

