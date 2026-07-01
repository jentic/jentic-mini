/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Overall usage statistics for a time window.
 */
export type UsageStatsBlock = {
    active_now: number;
    avg_ms: number;
    failed: number;
    p50_ms: (number | null);
    p95_ms: (number | null);
    pending: number;
    success: number;
    total: number;
};

