/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteConfidence } from './NoteConfidence';
import type { NoteResource } from './NoteResource';
import type { NoteSource } from './NoteSource';
import type { NoteType } from './NoteType';
/**
 * Payload for creating a new note.
 */
export type NoteCreateRequest = {
    body: string;
    confidence?: (NoteConfidence | null);
    related_execution_id?: (string | null);
    resource: NoteResource;
    source?: (NoteSource | null);
    type?: (NoteType | null);
};

