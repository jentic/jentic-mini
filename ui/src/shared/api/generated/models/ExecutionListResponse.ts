/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionResponse } from './ExecutionResponse';
/**
 * Paginated list of executions.
 */
export type ExecutionListResponse = {
    data: Array<ExecutionResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

