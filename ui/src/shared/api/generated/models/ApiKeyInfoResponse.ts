/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * API key metadata — retrievable even after revocation.
 */
export type ApiKeyInfoResponse = {
    created_at: string;
    created_by?: (string | null);
    id: string;
    rotated_at?: (string | null);
    status: string;
};

