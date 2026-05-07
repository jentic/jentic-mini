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
     * Generate (or regenerate) the default toolkit API key
     * Rotate the default `tk_xxx` key for the default toolkit (human session only).
     *
     * Only available when a default key was created in the past. New instances use agent identity
     * (OAuth DCR) for agent onboarding; toolkit keys remain valid for other uses.
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
        /**
         * Account credentials: username (trimmed of whitespace) and password (stored as bcrypt hash) for the root admin
         */
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
        /**
         * Login credentials: username and password for the root admin account
         */
        requestBody: {
            username: string;
            password: string;
        },
        /**
         * Redirect URL after successful login (relative path only)
         */
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
     * Returns current session info and authentication context.
     *
     * Response varies based on authentication method:
     * - Human session (JWT cookie): logged_in=true, includes username
     * - Trusted subnet (no auth): logged_in=false, admin=true (note about logging in for named session)
     * - Agent key (X-Jentic-API-Key): logged_in=false, agent_key=true, includes toolkit_id
     * - No auth: logged_in=false, agent_key=false
     *
     * Useful for UI to determine what features to show and whether to require login.
     * Agents can call this to confirm their key is valid and see which toolkit they belong to.
     *
     * This endpoint accepts requests with or without authentication (open passthrough).
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
        /**
         * OAuth2 password grant form: username, password, and grant_type='password' (form-urlencoded format)
         */
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
