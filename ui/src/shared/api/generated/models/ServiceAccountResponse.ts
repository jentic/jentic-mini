/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * ServiceAccount representation in API responses.
 */
export type ServiceAccountResponse = {
    approved_at?: (string | null);
    approved_by?: (string | null);
    created_at: string;
    denial_reason?: (string | null);
    denied_by?: (string | null);
    description?: (string | null);
    id: string;
    name: string;
    owner_id: string;
    registered_by: string;
    status: string;
};

