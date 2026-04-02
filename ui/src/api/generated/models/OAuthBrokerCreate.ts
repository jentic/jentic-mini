/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type OAuthBrokerCreate = {
    /**
     * Optional custom broker ID. Auto-generated from type if omitted.
     */
    id?: (string | null);
    /**
     * Broker backend type. Currently supported: `pipedream`.
     */
    type: string;
    /**
     * Provider-specific configuration. For `pipedream`: `client_id`, `client_secret`, `project_id` (all from Pipedream workspace → API settings → OAuth clients). Optional: `environment` (`production` or `development`, default `production`), `support_email`.
     */
    config: Record<string, any>;
};

