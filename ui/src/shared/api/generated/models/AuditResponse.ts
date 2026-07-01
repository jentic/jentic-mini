/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Audit entry representation in API responses.
 */
export type AuditResponse = {
    action: string;
    actor_id?: (string | null);
    actor_session_id?: (string | null);
    actor_type: string;
    after?: (Record<string, any> | null);
    before?: (Record<string, any> | null);
    diff?: (Record<string, any> | null);
    id: string;
    ip_address?: (string | null);
    job_id?: (string | null);
    occurred_at: string;
    origin?: (string | null);
    reason?: (string | null);
    request_id?: (string | null);
    target_id: string;
    target_parent_id?: (string | null);
    target_type: string;
    trace_id?: (string | null);
    user_agent?: (string | null);
};

