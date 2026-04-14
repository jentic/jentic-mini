/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Generate a Pipedream Connect Link for authorizing a new OAuth account. Returns URL for user authorization.
 */
export type ConnectLinkRequest = {
    /**
     * The Pipedream app slug to connect (e.g. `gmail`, `slack`, `github`, `stripe`). Required — Pipedream Connect Links must target a specific app. Find the slug via `GET /oauth-brokers/{id}/apps` or at pipedream.com/apps.
     */
    app: string;
    /**
     * A human-readable name for this connection, e.g. `work email` or `personal email`. Required because Pipedream only returns the app name ('Gmail'), not the account address — without a label there is no way to distinguish multiple accounts for the same app. This label is carried through to the resulting credential in `GET /credentials` and used when provisioning the credential to a toolkit. Must be non-empty — no silent fallbacks to app slug or API ID.
     */
    label: string;
    /**
     * The Jentic catalog API ID this connection maps to (e.g. `googleapis.com/gmail`). If provided, this overrides the automatic slug-map lookup during sync — the credential will be registered under exactly this API ID. Find the right ID via `GET /catalog?q=<name>`. If omitted, the slug map is used as a fallback (may not match the catalog ID).
     */
    api_id?: (string | null);
};

