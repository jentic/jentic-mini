/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OperationResultResponse } from './OperationResultResponse';
/**
 * Cursor-paginated search results page.
 */
export type SearchResponse = {
    data: Array<OperationResultResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

