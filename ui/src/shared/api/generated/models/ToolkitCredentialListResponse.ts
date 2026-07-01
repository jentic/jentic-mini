/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolkitCredentialBindingResponse } from './ToolkitCredentialBindingResponse';
/**
 * Paginated list of credential bindings.
 */
export type ToolkitCredentialListResponse = {
    data: Array<ToolkitCredentialBindingResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

