/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A slimmed parameter in an operation preview.
 */
export type PreviewParameterResponse = {
    /**
     * Parameter description (empty string when absent).
     */
    description: string;
    /**
     * OpenAPI parameter location.
     */
    in: string;
    /**
     * Parameter name.
     */
    name: string;
    /**
     * Whether the parameter is required.
     */
    required: boolean;
};

