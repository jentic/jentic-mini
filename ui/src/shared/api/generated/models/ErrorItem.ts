/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A granular error detail entry within the errors[] array of a ProblemDetails response.
 *
 * At least one of pointer, parameter, or header SHOULD be present to identify the error source.
 */
export type ErrorItem = {
    /**
     * An optional provider-specific code identifying this error in internal taxonomy or documentation.
     */
    code?: (string | null);
    /**
     * A human-readable explanation of this specific error. Be precise — name the field, parameter, or header involved.
     */
    detail: string;
    /**
     * The name of the request header that is the source of this error.
     */
    header?: (string | null);
    /**
     * The name of the query or path parameter that is the source of this error.
     */
    parameter?: (string | null);
    /**
     * A JSON Pointer (RFC 6901) to the specific request body property that is the source of this error.
     */
    pointer?: (string | null);
};

