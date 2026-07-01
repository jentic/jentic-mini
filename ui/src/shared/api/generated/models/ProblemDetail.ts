/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ErrorItem } from './ErrorItem';
/**
 * RFC 9457 Problem Details for HTTP APIs.
 *
 * This is the standard error response format for all Jentic APIs.
 * Content-Type: application/problem+json
 *
 * See: https://www.rfc-editor.org/rfc/rfc9457.html
 */
export type ProblemDetail = {
    /**
     * An optional provider-specific code for internal error taxonomy and observability correlation.
     */
    code?: (string | null);
    /**
     * A human-readable explanation specific to this occurrence of the problem. MUST be present. Provide actionable information where possible.
     */
    detail: string;
    /**
     * An array of granular error details. Use when multiple validation errors or field-level problems need to be surfaced in a single response.
     */
    errors?: (Array<ErrorItem> | null);
    /**
     * A URI reference identifying the specific occurrence of the problem. Typically the request path.
     */
    instance?: (string | null);
    /**
     * The HTTP status code for this occurrence of the problem.
     */
    status?: (number | null);
    /**
     * A short, human-readable summary of the problem type. Should not change between occurrences except for localisation purposes.
     */
    title?: (string | null);
    /**
     * A URI reference identifying the problem type. When set to 'about:blank', the title SHOULD be the standard HTTP status phrase. Use an IANA-registered type URI where one applies.
     */
    type?: string;
};

