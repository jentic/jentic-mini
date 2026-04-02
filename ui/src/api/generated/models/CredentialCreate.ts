/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CredentialCreate = {
    label: string;
    value: string;
    identity?: (string | null);
    api_id?: (string | null);
    /**
     * How this credential maps to the upstream API's authentication scheme. The broker uses this to find the right security scheme in the spec — it resolves by type, not by the bespoke scheme name in the overlay.
     *
     * | Value | Injects as | When to use |
     * |---|---|---|
     * | `bearer` | `Authorization: Bearer {value}` | REST APIs, OAuth access tokens, JWTs. GitHub REST API, Deepgram, Slack, etc. |
     * | `basic` | `Authorization: Basic base64({identity??'token'}:{value})` | HTTP Basic auth, git-over-HTTPS. Set `identity` to the username; omit for GitHub PATs (any username accepted). |
     * | `apiKey` | Custom header or query param `= {value}` | API key in a named header (X-API-Key, Api-Key, X-Auth-Key, etc.). For **compound** schemes (e.g. Discourse Api-Key + Api-Username) where the overlay uses canonical `Secret`/`Identity` scheme names, set `identity` to the username/account — a single credential covers both headers. |
     */
    auth_type?: ('bearer' | 'basic' | 'apiKey' | null);
};

