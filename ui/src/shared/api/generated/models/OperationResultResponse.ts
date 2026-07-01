/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiReferenceResponse } from './ApiReferenceResponse';
import type { SearchLinksResponse } from './SearchLinksResponse';
/**
 * A single search result matching the OperationResult spec.
 */
export type OperationResultResponse = {
    _links: SearchLinksResponse;
    api: ApiReferenceResponse;
    description?: (string | null);
    method: string;
    name?: (string | null);
    operation_id: string;
    relevance_score: number;
    type?: string;
    url: string;
};

