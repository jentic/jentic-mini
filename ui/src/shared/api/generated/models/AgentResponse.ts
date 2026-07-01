/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Agent representation in API responses.
 */
export type AgentResponse = {
    approved_at?: (string | null);
    approved_by?: (string | null);
    created_at: string;
    denial_reason?: (string | null);
    denied_by?: (string | null);
    description?: (string | null);
    has_api_key?: boolean;
    id: string;
    name: string;
    owner_id?: (string | null);
    parent_agent_id?: (string | null);
    registered_by: string;
    status: string;
};

