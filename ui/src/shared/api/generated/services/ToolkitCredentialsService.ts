/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolkitCredentialBindingResponse } from '../models/ToolkitCredentialBindingResponse';
import type { ToolkitCredentialBindRequest } from '../models/ToolkitCredentialBindRequest';
import type { ToolkitCredentialListResponse } from '../models/ToolkitCredentialListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ToolkitCredentialsService {
    /**
     * List toolkit credential bindings
     * List the credentials bound to a toolkit with cursor-based pagination.
     * @returns ToolkitCredentialListResponse Successful Response
     * @throws ApiError
     */
    public static listBindings({
        toolkitId,
        cursor,
        limit = 50,
    }: {
        toolkitId: string,
        cursor?: (string | null),
        limit?: number,
    }): CancelablePromise<ToolkitCredentialListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/credentials',
            path: {
                'toolkit_id': toolkitId,
            },
            query: {
                'cursor': cursor,
                'limit': limit,
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
     * Bind credential to toolkit
     * Bind an existing credential to a toolkit, optionally with inline permission rules.
     * @returns ToolkitCredentialBindingResponse Successful Response
     * @throws ApiError
     */
    public static bindCredential({
        toolkitId,
        requestBody,
    }: {
        toolkitId: string,
        requestBody: ToolkitCredentialBindRequest,
    }): CancelablePromise<ToolkitCredentialBindingResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/credentials',
            path: {
                'toolkit_id': toolkitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
                409: `Credential already bound`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Unbind credential from toolkit
     * Remove a credential binding from a toolkit (the credential itself is untouched).
     * @returns void
     * @throws ApiError
     */
    public static unbindCredential({
        toolkitId,
        credentialId,
    }: {
        toolkitId: string,
        credentialId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/toolkits/{toolkit_id}/credentials/{credential_id}',
            path: {
                'toolkit_id': toolkitId,
                'credential_id': credentialId,
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
}
