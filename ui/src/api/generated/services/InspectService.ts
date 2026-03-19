/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InspectService {
    /**
     * Inspect a capability — get full schema, auth, and parameters before calling
     * Returns everything needed to call an operation or workflow: resolved parameter schema
     * (all $refs inlined), response schema, auth translated to concrete header instructions,
     * API context (name, description, tag descriptions), and HATEOAS _links (execute, upstream).
     *
     * Capability id format: METHOD/host/path — e.g. GET/api.stripe.com/v1/customers
     * or POST/{jentic_hostname}/workflows/summarise-latest-topics.
     * Pass ?toolkit_id=... to check whether credentials are configured for that toolkit.
     * Accept: text/markdown returns a compact LLM-friendly format.
     * Accept: application/openapi+yaml returns the raw OpenAPI operation snippet.
     * @returns any Full capability detail — format controlled by Accept header.
     * @throws ApiError
     */
    public static getCapabilityInspectCapabilityIdGet({
        capabilityId,
        toolkitId,
    }: {
        capabilityId: string,
        /**
         * Pass to include credential status for this toolkit
         */
        toolkitId?: (string | null),
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/inspect/{capability_id}',
            path: {
                'capability_id': capabilityId,
            },
            query: {
                'toolkit_id': toolkitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
