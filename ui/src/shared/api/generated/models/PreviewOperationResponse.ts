/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreviewParameterResponse } from './PreviewParameterResponse';
/**
 * A slimmed operation in a catalog spec preview.
 */
export type PreviewOperationResponse = {
    /**
     * Operation description (empty string when absent).
     */
    description: string;
    /**
     * Upper-case HTTP method.
     */
    method: string;
    /**
     * OpenAPI operationId, when declared.
     */
    operation_id: (string | null);
    /**
     * Merged path- and operation-level parameters.
     */
    parameters: Array<PreviewParameterResponse>;
    /**
     * Operation path template.
     */
    path: string;
    /**
     * Flattened names of the security schemes that apply.
     */
    security: Array<string>;
    /**
     * Operation summary (empty string when absent).
     */
    summary: string;
    /**
     * Operation tags.
     */
    tags: Array<string>;
};

