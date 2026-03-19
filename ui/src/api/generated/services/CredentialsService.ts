/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CredentialCreate } from '../models/CredentialCreate';
import type { CredentialOut } from '../models/CredentialOut';
import type { CredentialPatch } from '../models/CredentialPatch';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CredentialsService {
    /**
     * Store an upstream API credential — add a secret to the vault for broker injection
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static createCredentialsPost({
        requestBody,
    }: {
        requestBody: CredentialCreate,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/credentials',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List upstream API credentials — labels and API bindings only, no secret values
     * List stored upstream API credentials. Values are never returned.
     *
     * All authenticated callers (agent keys and human sessions) can see all credential
     * labels and IDs — this is intentional. Labels are not secrets, and agents need
     * to discover credential IDs in order to file targeted `grant` access requests
     * (e.g. "bind Work Gmail" vs "bind Personal Gmail").
     *
     * Use `GET /credentials/{id}` to retrieve a specific credential by ID.
     * Filter with `?api_id=api.github.com` to list all credentials for a given API.
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static listCredentialsCredentialsGet({
        apiId,
    }: {
        apiId?: (string | null),
    }): CancelablePromise<Array<CredentialOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/credentials',
            query: {
                'api_id': apiId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get an upstream API credential by ID
     * Retrieve metadata for a single credential. Value is never returned.
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static getCredentialCredentialsCidGet({
        cid,
    }: {
        cid: string,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update an upstream API credential — rotate a secret or fix its API binding
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static patchCredentialsCidPatch({
        cid,
        requestBody,
    }: {
        cid: string,
        requestBody: CredentialPatch,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete an upstream API credential
     * @returns void
     * @throws ApiError
     */
    public static deleteCredentialsCidDelete({
        cid,
    }: {
        cid: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
