/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Update an existing credential. Only provided fields are changed. Rotates secrets without rebinding.
 */
export type CredentialPatch = {
    /**
     * New credential label (optional)
     */
    label?: (string | null);
    /**
     * New credential value for rotation (optional, encrypted before storage)
     */
    value?: (string | null);
    /**
     * New identity value (optional)
     */
    identity?: (string | null);
    /**
     * New API ID to rebind this credential (optional)
     */
    api_id?: (string | null);
    /**
     * Update the auth type for this credential. See `POST /credentials` for valid values and semantics.
     */
    auth_type?: ('bearer' | 'basic' | 'apiKey' | null);
};

