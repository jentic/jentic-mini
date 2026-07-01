/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PermissionRuleReadSchema } from './PermissionRuleReadSchema';
/**
 * Credential binding response.
 */
export type ToolkitCredentialBindingResponse = {
    api_name?: (string | null);
    api_vendor?: (string | null);
    bound_at: string;
    credential_id: string;
    credential_type?: (string | null);
    label?: (string | null);
    permissions?: Array<PermissionRuleReadSchema>;
    toolkit_id: string;
};

