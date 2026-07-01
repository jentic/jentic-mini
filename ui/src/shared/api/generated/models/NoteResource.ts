/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteApiReference } from './NoteApiReference';
/**
 * Exactly-one-of resource identifier for a note (request side).
 */
export type NoteResource = {
    api?: (NoteApiReference | null);
    credential_id?: (string | null);
    execution_id?: (string | null);
    operation_id?: (string | null);
};

