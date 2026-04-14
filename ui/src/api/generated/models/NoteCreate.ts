/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Create a note on any Jentic resource for knowledge accumulation and catalog improvement.
 */
export type NoteCreate = {
    /**
     * Resource identifier: operation_id (METHOD/host/path), api_id, or workflow slug
     */
    resource: string;
    /**
     * Note category: 'auth_quirk', 'usage_hint', 'execution_feedback', or 'correction'
     */
    type?: (string | null);
    /**
     * Note content — be specific and actionable
     */
    note: string;
    /**
     * Link to specific execution for context (optional)
     */
    execution_id?: (string | null);
    /**
     * Confidence level: 'observed', 'suspected', or 'verified'
     */
    confidence?: (string | null);
    /**
     * Observation source, e.g. 'test run', 'production', 'documentation'
     */
    source?: (string | null);
};

