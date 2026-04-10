/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for syncing discovered OAuth accounts from a broker into Jentic credentials.
 */
export type SyncRequest = {
    /**
     * The user identity to sync accounts for. In a single-user setup this is always `default`. In multi-user deployments, pass the Jentic user ID that was used when the user completed OAuth in Pipedream's hosted UI.
     */
    external_user_id?: string;
};

