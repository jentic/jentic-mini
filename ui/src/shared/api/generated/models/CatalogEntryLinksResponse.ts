/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Hypermedia links for a catalog entry.
 */
export type CatalogEntryLinksResponse = {
    /**
     * Human-facing GitHub tree URL for the entry, when known.
     */
    github?: (string | null);
    /**
     * URL of the catalog import action (`POST /catalog/{api_id}:import`).
     */
    import: string;
    /**
     * URL of the entry's operation preview.
     */
    operations: string;
    /**
     * Canonical URL of this catalog entry.
     */
    self: string;
};

