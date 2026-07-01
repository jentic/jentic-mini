/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for setting a provider config.
 *
 * Fields are provider-specific and validated server-side by provider name.
 * For ``pipedream`` the recognised fields are ``project_id``, ``client_id``,
 * ``client_secret`` (write-only), and optional ``environment``,
 * ``connect_base_url``, ``expiry_skew_seconds``.
 */
export type ProviderConfigSetRequest = {
    /**
     * Provider-specific configuration fields, validated by provider name.
     */
    config: Record<string, any>;
};

