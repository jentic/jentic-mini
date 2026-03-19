/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ExecuteService {
    /**
     * Broker — proxy a call to any registered API with automatic credential injection
     * Routes any HTTP request to the upstream API, injecting credentials automatically.
     *
     * URL shape: `/{upstream_host}/{path}` — e.g. `/api.stripe.com/v1/customers`
     *
     * All HTTP methods supported; Swagger UI shows GET as representative.
     *
     * **Headers:**
     * - `X-Jentic-Simulate: true` — validate and preview the call without sending it
     * - `X-Jentic-Credential: {alias}` — select a specific credential when multiple exist for an API
     * - `X-Jentic-Dry-Run: true` — alias for Simulate (deprecated)
     *
     * Returns upstream response verbatim plus `X-Jentic-Execution-Id` for trace correlation.
     * @returns any Upstream response proxied verbatim. Content-Type matches upstream.
     * @throws ApiError
     */
    public static brokerGet({
        target,
    }: {
        target: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/{target}',
            path: {
                'target': target,
            },
            errors: {
                400: `Bad request (upstream or Jentic validation)`,
                401: `Missing or rejected credential`,
                403: `Policy denied or upstream forbidden`,
                404: `Upstream resource not found`,
                422: `Validation Error`,
                502: `Upstream unreachable`,
            },
        });
    }
}
