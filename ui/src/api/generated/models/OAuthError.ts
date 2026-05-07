/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * RFC 6749 §5.2 / RFC 7591 §3.2.2 error response body.
 *
 * OAuth routes intentionally bypass FastAPI's HTTPException → ``{"detail": ...}``
 * convention so the wire shape matches the spec.
 */
export type OAuthError = {
    /**
     * OAuth error code (e.g. 'invalid_grant').
     */
    error: string;
    /**
     * Human-readable description; safe to log, not safe to display.
     */
    error_description?: (string | null);
};

