/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * OAuth broker configuration with discovered accounts count. Config excludes sensitive fields.
 */
export type OAuthBrokerOut = {
    /**
     * Broker ID (format: broker_{12chars})
     */
    id: string;
    /**
     * Broker type: 'pipedream' or other provider
     */
    type: string;
    /**
     * Public broker configuration (excludes encrypted secret fields)
     */
    config: Record<string, any>;
    /**
     * Unix timestamp when broker was registered
     */
    created_at: number;
    /**
     * Number of OAuth accounts discovered from this broker
     */
    accounts_discovered?: number;
};

