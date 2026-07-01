/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteConfidence } from './NoteConfidence';
import type { NoteSource } from './NoteSource';
import type { NoteType } from './NoteType';
/**
 * Payload for updating an existing note (partial).
 */
export type NoteUpdateRequest = {
    body?: (string | null);
    confidence?: (NoteConfidence | null);
    related_execution_id?: (string | null);
    source?: (NoteSource | null);
    type?: (NoteType | null);
};

