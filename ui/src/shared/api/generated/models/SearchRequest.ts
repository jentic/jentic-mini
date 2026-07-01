/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /search request body.
 */
export type SearchRequest = {
    apis?: (Array<string> | null);
    cursor?: (string | null);
    limit?: number;
    query: string;
    revision_pins?: (Record<string, string> | null);
};

