/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single event in the API key audit trail.
 */
export type ApiKeyHistoryEntryResponse = {
    action: string;
    actor_id?: (string | null);
    id: string;
    occurred_at: string;
    reason?: (string | null);
};

