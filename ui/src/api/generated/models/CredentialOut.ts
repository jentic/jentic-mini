/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Upstream API credential metadata. Secret values are never returned after creation.
 */
export type CredentialOut = {
    /**
     * Credential ID
     */
    id: string;
    /**
     * Human-readable label for this credential
     */
    label: string;
    /**
     * Identity field (username, client ID, etc.) for basic auth or compound API key schemes
     */
    identity?: (string | null);
    /**
     * API this credential is bound to
     */
    api_id?: (string | null);
    /**
     * Auth type: bearer, basic, or apiKey
     */
    auth_type?: (string | null);
    /**
     * Unix timestamp when created
     */
    created_at?: (number | null);
    /**
     * Unix timestamp of last update
     */
    updated_at?: (number | null);
    /**
     * OAuth broker account ID (if from OAuth broker)
     */
    account_id?: (string | null);
    /**
     * OAuth app slug (if from OAuth broker)
     */
    app_slug?: (string | null);
    /**
     * Unix timestamp of last OAuth sync
     */
    synced_at?: (number | null);
};

