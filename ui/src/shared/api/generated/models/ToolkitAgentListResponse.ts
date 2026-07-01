/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolkitAgentResponse } from './ToolkitAgentResponse';
/**
 * Paginated list of agents bound to a toolkit.
 */
export type ToolkitAgentListResponse = {
    data: Array<ToolkitAgentResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

