/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthResponse } from '../models/HealthResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SystemService {
    /**
     * Health
     * Return admin service health status.
     * @returns HealthResponse Successful Response
     * @throws ApiError
     */
    public static health(): CancelablePromise<HealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/health',
            errors: {
                400: `Bad Request`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Auth health
     * Return service health status for this surface.
     *
     * Unauthenticated liveness probe. In combined mode this is served under
     * the surface prefix (e.g. ``/control/health``) so surfaces don't collide;
     * the canonical platform probe is the root ``GET /health``.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static authHealth(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/health',
            errors: {
                400: `Bad Request`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Control health
     * Return service health status for this surface.
     *
     * Unauthenticated liveness probe. In combined mode this is served under
     * the surface prefix (e.g. ``/control/health``) so surfaces don't collide;
     * the canonical platform probe is the root ``GET /health``.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static controlHealth(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/control/health',
            errors: {
                400: `Bad Request`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Health
     * Liveness probe for the combined control-plane app.
     *
     * Unauthenticated and dependency-free so orchestrators and load balancers
     * have a stable target. Returns ``{"status": "ok"}`` when the process is up.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getHealth(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Registry health
     * Return service health status for this surface.
     *
     * Unauthenticated liveness probe. In combined mode this is served under
     * the surface prefix (e.g. ``/control/health``) so surfaces don't collide;
     * the canonical platform probe is the root ``GET /health``.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static registryHealth(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/registry/health',
            errors: {
                400: `Bad Request`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
}
