/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionListResponse } from '../models/ExecutionListResponse';
import type { ExecutionResponse } from '../models/ExecutionResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ExecutionsService {
    /**
     * List Executions
     * List execution records with optional filters.
     * @returns ExecutionListResponse Successful Response
     * @throws ApiError
     */
    public static listExecutions({
        toolkitId,
        traceId,
        status,
        from,
        to,
        api,
        actorId,
        origin,
        cursor,
        limit = 25,
    }: {
        toolkitId?: (string | null),
        traceId?: (string | null),
        status?: (Array<string> | null),
        from?: (string | null),
        to?: (string | null),
        api?: (string | null),
        actorId?: (string | null),
        origin?: (string | null),
        cursor?: (string | null),
        limit?: number,
    }): CancelablePromise<ExecutionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/executions',
            query: {
                'toolkit_id': toolkitId,
                'trace_id': traceId,
                'status': status,
                'from': from,
                'to': to,
                'api': api,
                'actor_id': actorId,
                'origin': origin,
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
     * Get Execution
     * Get an execution record by ID.
     * @returns ExecutionResponse Successful Response
     * @throws ApiError
     */
    public static getExecution({
        executionId,
    }: {
        executionId: string,
    }): CancelablePromise<ExecutionResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/executions/{execution_id}',
            path: {
                'execution_id': executionId,
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
