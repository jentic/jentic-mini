/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CredentialRedactedResponse } from './CredentialRedactedResponse';
/**
 * Paginated list of credentials.
 */
export type CredentialListResponse = {
    data: Array<CredentialRedactedResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

