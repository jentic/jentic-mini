/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ServiceAccountResponse } from './ServiceAccountResponse';
/**
 * List of service accounts.
 */
export type ServiceAccountListResponse = {
    data: Array<ServiceAccountResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

