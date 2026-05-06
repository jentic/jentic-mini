/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Health response when no admin account exists yet.
 *
 * Carries the URLs an agent or human needs to bootstrap: the OAuth metadata
 * document for agent DCR, the canonical token / registration endpoints, and
 * the human-facing setup_url for admin-account creation.
 */
export type HealthSetupRequired = {
    /**
     * Bootstrap state — no admin account exists
     */
    status: string;
    account_created: boolean;
    message: string;
    next_step: string;
    /**
     * Human-facing URL to create the admin account
     */
    setup_url: string;
    /**
     * Discovery document URL for agent DCR (RFC 8414)
     */
    oauth_authorization_server_metadata: string;
    registration_endpoint: string;
    token_endpoint: string;
    version: string;
};

