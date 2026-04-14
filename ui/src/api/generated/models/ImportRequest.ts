/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImportSource } from './ImportSource';
/**
 * Batch import request for multiple OpenAPI specs or Arazzo workflows. Sources processed in parallel.
 */
export type ImportRequest = {
    /**
     * Array of import sources (OpenAPI specs or Arazzo workflows) to register in the catalog
     */
    sources: Array<ImportSource>;
};

