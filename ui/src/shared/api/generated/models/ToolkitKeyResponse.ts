/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Toolkit key response.
 */
export type ToolkitKeyResponse = {
    allowed_ips?: (Array<string> | null);
    created_at: string;
    key_id: string;
    key_preview: string;
    label?: (string | null);
    last_used_at?: (string | null);
    revoked: boolean;
    toolkit_id: string;
};

