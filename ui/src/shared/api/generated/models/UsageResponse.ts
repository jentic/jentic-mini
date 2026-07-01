/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UsageBucket } from './UsageBucket';
import type { UsageStatsBlock } from './UsageStatsBlock';
import type { UsageTopRow } from './UsageTopRow';
/**
 * Full usage statistics response.
 */
export type UsageResponse = {
    bucket_seconds: number;
    buckets: Array<UsageBucket>;
    group_by: string;
    since: number;
    stats: UsageStatsBlock;
    top: Array<UsageTopRow>;
    until: number;
};

