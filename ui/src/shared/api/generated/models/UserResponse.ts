/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Permissions } from './Permissions';
/**
 * User representation in API responses.
 */
export type UserResponse = {
    active: boolean;
    auth_provider: string;
    created_at: string;
    email: string;
    external_subject_id?: (string | null);
    first_name: string;
    id: string;
    invite_state: string;
    last_name: string;
    must_change_password: boolean;
    name: string;
    permissions: Permissions;
    updated_at?: (string | null);
};

