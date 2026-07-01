/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OperationSummaryResponse } from './OperationSummaryResponse';
/**
 * Cursor-paginated list of operations.
 */
export type OperationSummaryListResponse = {
    data: Array<OperationSummaryResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

