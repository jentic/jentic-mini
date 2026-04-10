/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Update OAuth broker configuration. Only provided fields are changed; secrets remain encrypted.
 */
export type OAuthBrokerUpdate = {
    /**
     * Updated provider-specific configuration. For `pipedream`: `client_id`, `client_secret`, `project_id` are all accepted. Fields not supplied are left unchanged. `client_secret` is write-only — Fernet-encrypted at rest, never returned.
     */
    config: Record<string, any>;
};

