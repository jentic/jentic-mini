/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserResponse } from './UserResponse';
/**
 * Paginated list of users.
 */
export type UserListResponse = {
    data: Array<UserResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

