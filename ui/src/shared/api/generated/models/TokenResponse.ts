/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Token endpoint success response.
 */
export type TokenResponse = {
    access_token: string;
    expires_in: number;
    id_token?: (string | null);
    refresh_token?: (string | null);
    token_type?: string;
};

