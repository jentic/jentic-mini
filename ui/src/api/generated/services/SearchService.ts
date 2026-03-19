/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SearchResult } from '../models/SearchResult';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SearchService {
    /**
     * Search the catalog — find operations and workflows by natural language intent
     * BM25 search over all registered API operations, Arazzo workflows, and the Jentic public API catalog.
     *
     * Returns id, summary, description (≤3 sentences), type, score, and _links.
     * - `source: "local"` — operation or workflow in your local registry
     * - `source: "catalog"` — API available from the Jentic public catalog; add credentials to use
     *
     * _links.inspect → GET /inspect/{id} for full schema and auth detail.
     * _links.execute → broker URL to call directly once ready.
     * Typical flow: search → inspect → execute.
     * @returns SearchResult Successful Response
     * @throws ApiError
     */
    public static searchSearchGet({
        q,
        n = 10,
    }: {
        /**
         * Search query, e.g. "send an email" or "create payment"
         */
        q: string,
        /**
         * Number of results to return
         */
        n?: number,
    }): CancelablePromise<Array<SearchResult>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/search',
            query: {
                'q': q,
                'n': n,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
