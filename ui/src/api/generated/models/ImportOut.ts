/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result of importing an OpenAPI spec or Arazzo workflow into the catalog.
 *
 * The import endpoint (POST /import) accepts specs from URLs, local file paths, or
 * inline content. It parses the document, indexes operations/workflows in BM25,
 * and stores metadata for broker execution. Returns the registered ID and count
 * of indexed operations.
 */
export type ImportOut = Record<string, any>;
