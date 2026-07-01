/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserResponse } from './UserResponse';
/**
 * Response after user creation including invite token.
 */
export type UserCreatedResponse = {
    invite_expires_at: string;
    invite_token: string;
    user: UserResponse;
};

