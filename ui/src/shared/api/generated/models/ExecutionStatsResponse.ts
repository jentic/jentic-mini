/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DailyExecutionBucket } from './DailyExecutionBucket';
import type { TopOperation } from './TopOperation';
/**
 * Aggregated execution statistics for the dashboard.
 */
export type ExecutionStatsResponse = {
    daily_buckets: Array<DailyExecutionBucket>;
    success_rate_percent: number;
    top_operations: Array<TopOperation>;
    total_executions: number;
};

