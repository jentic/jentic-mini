/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProviderConfigListResponse } from '../models/ProviderConfigListResponse';
import type { ProviderConfigResponse } from '../models/ProviderConfigResponse';
import type { ProviderConfigSetRequest } from '../models/ProviderConfigSetRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConfigurationService {
    /**
     * List credential provider configs
     * List all stored provider configs, with secret fields redacted.
     * @returns ProviderConfigListResponse Successful Response
     * @throws ApiError
     */
    public static listProviderConfigs(): CancelablePromise<ProviderConfigListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/config/providers',
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Get a credential provider config
     * Get a stored provider config by name, with secret fields redacted.
     * @returns ProviderConfigResponse Successful Response
     * @throws ApiError
     */
    public static getProviderConfig({
        name,
    }: {
        name: string,
    }): CancelablePromise<ProviderConfigResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/config/providers/{name}',
            path: {
                'name': name,
            },
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Set a credential provider config
     * Set (create or update) a credential provider config at runtime.
     *
     * The payload is validated by provider name (e.g. ``pipedream``). Secret fields
     * are encrypted at rest. A successful write rebuilds the in-process provider
     * registry so the change takes effect without a restart. The response redacts
     * secret fields.
     * @returns ProviderConfigResponse Successful Response
     * @throws ApiError
     */
    public static setProviderConfig({
        name,
        requestBody,
    }: {
        name: string,
        requestBody: ProviderConfigSetRequest,
    }): CancelablePromise<ProviderConfigResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/admin/config/providers/{name}',
            path: {
                'name': name,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
}
