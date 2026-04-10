/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for creating the root admin account. One-time only — POST /user/create returns 410 after first use.
 */
export type UserCreate = {
    /**
     * Admin account username (will be trimmed of whitespace)
     */
    username: string;
    /**
     * Admin account password (stored as bcrypt hash)
     */
    password: string;
};

