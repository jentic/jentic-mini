/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Structured description of an API's authentication scheme.
 *
 * Jentic generates the OpenAPI overlay from this; no need to write overlay YAML.
 * Multiple entries can be submitted in one call for APIs requiring more than
 * one header (e.g. Discourse needs Api-Key + Api-Username).
 */
export type SchemeInput = {
    type: SchemeInput.type;
    in?: ('header' | 'query' | 'cookie' | null);
    name?: (string | null);
    token_url?: (string | null);
    openid_connect_url?: (string | null);
    scheme_name?: (string | null);
    contributed_by?: (string | null);
};
export namespace SchemeInput {
    export enum type {
        API_KEY = 'apiKey',
        BEARER = 'bearer',
        BASIC = 'basic',
        OAUTH2_CLIENT_CREDENTIALS = 'oauth2_client_credentials',
        OPEN_ID_CONNECT = 'openIdConnect',
    }
}

