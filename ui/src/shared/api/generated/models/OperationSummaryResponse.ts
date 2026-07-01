/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiReferenceResponse } from './ApiReferenceResponse';
import type { OperationSummaryLinksResponse } from './OperationSummaryLinksResponse';
/**
 * Single operation in a paginated list.
 */
export type OperationSummaryResponse = {
    _links: OperationSummaryLinksResponse;
    api: ApiReferenceResponse;
    deprecated?: boolean;
    description?: (string | null);
    method: string;
    name?: (string | null);
    operation_id: string;
    path: string;
    revision_id: string;
    tags?: Array<string>;
};

