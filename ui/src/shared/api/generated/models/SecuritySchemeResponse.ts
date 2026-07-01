/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SecuritySchemeFlowResponse } from './SecuritySchemeFlowResponse';
/**
 * Full security scheme detail for a revision.
 */
export type SecuritySchemeResponse = {
    bearer_format?: (string | null);
    description?: (string | null);
    flows?: Array<SecuritySchemeFlowResponse>;
    in_location?: (string | null);
    name: string;
    open_id_connect_url?: (string | null);
    param_name?: (string | null);
    scheme?: (string | null);
    type: string;
};

