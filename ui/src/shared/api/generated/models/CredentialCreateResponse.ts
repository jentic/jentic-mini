/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CredentialRedactedResponse } from './CredentialRedactedResponse';
/**
 * Create response: redacted + secret shown once.
 */
export type CredentialCreateResponse = {
    credential: CredentialRedactedResponse;
    secret: Record<string, any>;
};

