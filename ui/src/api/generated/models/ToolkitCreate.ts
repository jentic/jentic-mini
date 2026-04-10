/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Create a new toolkit with scoped credentials and access control. Optionally generates first API key.
 */
export type ToolkitCreate = {
    /**
     * Toolkit name for identification
     */
    name: string;
    /**
     * Optional description of this toolkit's purpose
     */
    description?: (string | null);
    /**
     * If true, toolkit operates in dry-run mode (no real API calls)
     */
    simulate?: boolean;
    /**
     * Label for the first key created with this toolkit (e.g. 'Agent A')
     */
    initial_key_label?: (string | null);
    /**
     * IP allowlist for the first key. NULL = unrestricted.
     */
    initial_key_allowed_ips?: (Array<string> | null);
};

