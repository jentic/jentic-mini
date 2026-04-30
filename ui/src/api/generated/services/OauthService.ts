/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_oauth_revoke_oauth_revoke_post } from '../models/Body_oauth_revoke_oauth_revoke_post';
import type { Body_oauth_token_oauth_token_post } from '../models/Body_oauth_token_oauth_token_post';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class OauthService {
    /**
     * OAuth 2.0 Authorization Server Metadata (RFC 8414)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static oauthAuthorizationServerMetadataWellKnownOauthAuthorizationServerGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/.well-known/oauth-authorization-server',
        });
    }
    /**
     * OAuth 2.0 token revocation (RFC 7009)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static oauthRevokeOauthRevokePost({
        formData,
    }: {
        formData?: Body_oauth_revoke_oauth_revoke_post,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/oauth/revoke',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * OAuth 2.0 token endpoint
     * @returns any Successful Response
     * @throws ApiError
     */
    public static oauthTokenOauthTokenPost({
        formData,
    }: {
        formData?: Body_oauth_token_oauth_token_post,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/oauth/token',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Dynamic Client Registration (RFC 7591)
     * Register an agent identity (client_name + jwks). Returns pending status until a human approves.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static dynamicClientRegistrationRegisterPost({
        requestBody,
    }: {
        requestBody: Record<string, any>,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read client registration (RFC 7592)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getRegistrationRegisterClientIdGet({
        clientId,
    }: {
        clientId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/register/{client_id}',
            path: {
                'client_id': clientId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
