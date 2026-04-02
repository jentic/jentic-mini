/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CredentialPatch = {
    label?: (string | null);
    value?: (string | null);
    identity?: (string | null);
    api_id?: (string | null);
    /**
     * Update the auth type for this credential. See `POST /credentials` for valid values and semantics.
     */
    auth_type?: ('bearer' | 'basic' | 'apiKey' | null);
};

