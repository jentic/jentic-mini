/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_token_user_token_post } from '../models/Body_token_user_token_post';
import type { UserCreate } from '../models/UserCreate';
import type { UserOut } from '../models/UserOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UserService {
    /**
     * Generate (or regenerate) the default agent API key
     * Issue the default `tk_xxx` agent key bound to the default toolkit.
     *
     * **First call** — unauthenticated, subnet-restricted:
     * - Available only before the key has been claimed
     * - Only accessible from trusted subnets (RFC 1918 + loopback by default;
     * configure via `JENTIC_TRUSTED_SUBNETS` env var)
     * - Returns the key **once only** — it is not recoverable after this response
     * - After this call, the endpoint requires a human session
     *
     * **Subsequent calls** — human session required:
     * - Revokes the current default key
     * - Issues and returns a fresh key
     *
     * The key works immediately — you do not need to wait for the admin account
     * to be created before using it.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateDefaultKeyDefaultApiKeyGeneratePost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/default-api-key/generate',
        });
    }
    /**
     * Create the root admin account (one-time setup)
     * Create the single root account for this instance.
     *
     * This endpoint is available **once only**. After the first call it returns
     * `410 Gone`. There is no multi-user system — one human owns this instance.
     *
     * Requires `bcrypt` installed (bundled in Docker image).
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createUserUserCreatePost({
        requestBody,
    }: {
        requestBody: UserCreate,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/user/create',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Log in and receive a session cookie
     * Authenticate with username and password.
     *
     * Accepts JSON body (`{"username": ..., "password": ...}`) or HTML form data.
     * Returns an httpOnly JWT session cookie valid for 30 days (sliding window).
     *
     * Pass `?redirect_to=/docs` to redirect after a successful browser form login.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static loginUserLoginPost({
        requestBody,
        redirectTo,
    }: {
        requestBody: {
            username: string;
            password: string;
        },
        redirectTo?: (string | null),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/user/login',
            query: {
                'redirect_to': redirectTo,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Log out — clear the session cookie
     * Terminate the current human session.
     *
     * Clears the `jentic_session` httpOnly cookie if present. If you authenticated
     * via Bearer token (Swagger UI OAuth2 flow), discard the token on your end —
     * there is no server-side token store to invalidate.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static logoutUserLogoutPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/user/logout',
        });
    }
    /**
     * Check current session status
     * Returns current session info. Useful for UI to check if logged in.
     * @returns UserOut Successful Response
     * @throws ApiError
     */
    public static meUserMeGet(): CancelablePromise<UserOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/me',
        });
    }
    /**
     * OAuth2 password grant — returns Bearer JWT
     * OAuth2 password grant endpoint.
     *
     * Swagger UI's **Authorize** dialog uses this automatically when you fill in
     * the *HumanLogin* username + password fields. Returns a Bearer JWT that
     * Swagger UI injects as `Authorization: Bearer ...` on all subsequent calls.
     *
     * This is functionally equivalent to `POST /user/login` but returns the token
     * in the response body rather than as a cookie — the standard OAuth2 pattern
     * expected by Swagger UI.
     * @returns any Access token for use in Authorization: Bearer header
     * @throws ApiError
     */
    public static tokenUserTokenPost({
        formData,
    }: {
        formData: Body_token_user_token_post,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/user/token',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
