/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type KeyCreate = {
    /**
     * Human-readable label, e.g. 'Agent A', 'Staging bot'
     */
    label?: (string | null);
    /**
     * IP allowlist for this key only. NULL = unrestricted.
     */
    allowed_ips?: (Array<string> | null);
};

