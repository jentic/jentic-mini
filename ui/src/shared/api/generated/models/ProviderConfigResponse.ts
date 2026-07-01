/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A stored provider config with secret fields redacted.
 */
export type ProviderConfigResponse = {
    /**
     * Stored config with secret fields redacted.
     */
    config: Record<string, any>;
    created_at: string;
    /**
     * Provider name (e.g. 'pipedream').
     */
    name: string;
    updated_at?: (string | null);
};

