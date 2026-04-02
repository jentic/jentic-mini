/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminService {
    /**
     * Refresh the API catalog manifest from GitHub
     * Rebuilds the internal catalog manifest from the jentic/jentic-public-apis repository.
     * The manifest is used by lazy import — when you `POST /credentials` for an API not yet in
     * your local registry, Jentic Mini resolves the spec from this manifest automatically.
     *
     * Takes ~2–5 seconds (two unauthenticated GitHub API calls). Safe to call repeatedly.
     * The manifest auto-refreshes daily; only call this explicitly if you need immediate sync
     * after a new API has been added to the public catalog.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static refreshCatalogCatalogRefreshPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/catalog/refresh',
        });
    }
}
