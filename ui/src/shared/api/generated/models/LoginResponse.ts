/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * JWT token response after successful authentication.
 */
export type LoginResponse = {
    access_token: string;
    expires_in: number;
    must_change_password: boolean;
    token_type: string;
};

