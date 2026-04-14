/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A search result from the BM25 index — either an operation or workflow capability.
 *
 * The BM25 search index covers both API operations (parsed from OpenAPI specs) and
 * workflows (parsed from Arazzo documents). Results are ranked by relevance score.
 * Use GET /inspect/{id} to get the full schema for a result before calling it.
 */
export type SearchResult = Record<string, any>;
