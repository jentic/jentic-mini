/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OperationSummaryListResponse } from '../models/OperationSummaryListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiOperationsService {
    /**
     * List Api Operations
     * List operations for the API's current (live) revision.
     * @returns OperationSummaryListResponse Successful Response
     * @throws ApiError
     */
    public static listApiOperations({
        vendor,
        name,
        version,
        cursor,
        limit = 50,
    }: {
        vendor: string,
        name: string,
        version: string,
        cursor?: (string | null),
        limit?: number,
    }): CancelablePromise<OperationSummaryListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{vendor}/{name}/{version}/operations',
            path: {
                'vendor': vendor,
                'name': name,
                'version': version,
            },
            query: {
                'cursor': cursor,
                'limit': limit,
            },
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
     * List Api Revision Operations
     * List operations for a specific revision.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listApiRevisionOperations({
        vendor,
        name,
        version,
        revisionId,
        cursor,
        limit = 50,
    }: {
        vendor: string,
        name: string,
        version: string,
        revisionId: string,
        cursor?: (string | null),
        limit?: number,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{vendor}/{name}/{version}/revisions/{revision_id}/operations',
            path: {
                'vendor': vendor,
                'name': name,
                'version': version,
                'revision_id': revisionId,
            },
            query: {
                'cursor': cursor,
                'limit': limit,
            },
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
