/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Current user profile.
 */
export type CurrentUserResponse = {
    active: boolean;
    created_at: string;
    email: string;
    first_name: string;
    id: string;
    last_name: string;
    must_change_password: boolean;
    permissions: Array<string>;
    updated_at?: (string | null);
};

