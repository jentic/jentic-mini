/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolkitResponse } from './ToolkitResponse';
/**
 * Paginated list of toolkits.
 */
export type ToolkitListResponse = {
    data: Array<ToolkitResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

