/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionStatsResponse } from '../models/ExecutionStatsResponse';
import type { GroupBy } from '../models/GroupBy';
import type { UsageResponse } from '../models/UsageResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MonitoringService {
    /**
     * Get Execution Stats
     * Return aggregated execution statistics for the dashboard.
     * @returns ExecutionStatsResponse Successful Response
     * @throws ApiError
     */
    public static getExecutionStats({
        days = 7,
    }: {
        days?: number,
    }): CancelablePromise<ExecutionStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/monitoring/executions',
            query: {
                'days': days,
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
     * Get Usage Stats
     * Return detailed usage statistics for the monitoring overview.
     * @returns UsageResponse Successful Response
     * @throws ApiError
     */
    public static getUsageStats({
        since,
        until,
        groupBy,
        topLimit = 10,
        toolkitId,
        apiId,
        agentId,
        status,
    }: {
        since?: (number | null),
        until?: (number | null),
        groupBy?: (GroupBy | null),
        topLimit?: number,
        toolkitId?: (string | null),
        apiId?: (string | null),
        agentId?: (string | null),
        status?: (string | null),
    }): CancelablePromise<UsageResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/monitoring/usage',
            query: {
                'since': since,
                'until': until,
                'group_by': groupBy,
                'top_limit': topLimit,
                'toolkit_id': toolkitId,
                'api_id': apiId,
                'agent_id': agentId,
                'status': status,
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
