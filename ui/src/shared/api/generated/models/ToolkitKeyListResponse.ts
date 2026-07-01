/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolkitKeyResponse } from './ToolkitKeyResponse';
/**
 * Paginated list of toolkit keys.
 */
export type ToolkitKeyListResponse = {
    data: Array<ToolkitKeyResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

