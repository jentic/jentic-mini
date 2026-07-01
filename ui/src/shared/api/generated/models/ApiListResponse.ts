/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse } from './ApiResponse';
/**
 * Cursor-paginated list of APIs.
 */
export type ApiListResponse = {
    data: Array<ApiResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

