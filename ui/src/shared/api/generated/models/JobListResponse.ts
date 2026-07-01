/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JobResponse } from './JobResponse';
/**
 * Paginated list of jobs.
 */
export type JobListResponse = {
    data: Array<JobResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

