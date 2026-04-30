/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MetaService {
    /**
     * Health
     * Returns current setup state with explicit instructions for agents and UI.
     *
     * Response varies based on setup progress:
     * - status='setup_required': No admin account yet → OAuth metadata URLs for agent DCR; human setup_url
     * - status='ok': Admin account exists → includes version and apis_registered count
     *
     * This endpoint is always public (no auth required) so agents can check setup state before
     * attempting authenticated calls. UI uses this to determine whether to show setup wizard.
     *
     * Returns:
     * Setup status, version, and context-specific next steps or operational metrics.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Get Version
     * Returns current version and latest GitHub release (cached 6 h).
     * Set JENTIC_TELEMETRY=off to disable the outbound GitHub check.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getVersionVersionGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/version',
        });
    }
}
