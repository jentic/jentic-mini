/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Create a note on any Jentic resource.
 *
 * resource: the resource identifier (operation_id, api_id, workflow slug)
 * type: categorize the note for filtering and analysis
 * note: the content — be specific and actionable
 * execution_id: link to a specific execution (optional)
 * confidence: how certain are you?
 * source: where did you observe this?
 */
export type NoteCreate = {
    resource: string;
    type?: (string | null);
    note: string;
    execution_id?: (string | null);
    confidence?: (string | null);
    source?: (string | null);
};

