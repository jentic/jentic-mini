/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type GrantsReplaceBody = {
    /**
     * The complete set of toolkit_ids the agent should be granted after this call. Existing grants not in this list will be revoked. Toolkits in this list that the agent does not yet have a grant on will be added. Atomic: either all changes apply or none do.
     */
    toolkit_ids: Array<string>;
};

