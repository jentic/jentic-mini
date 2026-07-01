/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentResponse } from './AgentResponse';
/**
 * List of agents.
 */
export type AgentListResponse = {
    data: Array<AgentResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

