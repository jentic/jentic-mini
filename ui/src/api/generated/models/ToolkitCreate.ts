/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ToolkitCreate = {
    name: string;
    description?: (string | null);
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

