/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditResponse } from './AuditResponse';
/**
 * Paginated list of audit entries.
 */
export type AuditListResponse = {
    data: Array<AuditResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

