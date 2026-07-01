/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteCreateRequest } from '../models/NoteCreateRequest';
import type { NoteUpdateRequest } from '../models/NoteUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class NotesService {
    /**
     * List Notes
     * List notes with optional filters and cursor pagination.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listNotes({
        cursor,
        limit = 50,
        api,
        operationId,
        executionId,
        credentialId,
        type,
        createdBy,
    }: {
        cursor?: (string | null),
        limit?: number,
        api?: (string | null),
        operationId?: (string | null),
        executionId?: (string | null),
        credentialId?: (string | null),
        type?: (string | null),
        createdBy?: (string | null),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/notes',
            query: {
                'cursor': cursor,
                'limit': limit,
                'api': api,
                'operation_id': operationId,
                'execution_id': executionId,
                'credential_id': credentialId,
                'type': type,
                'created_by': createdBy,
            },
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Create Note
     * Create a new note attached to a registry resource.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createNote({
        requestBody,
    }: {
        requestBody: NoteCreateRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/notes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Delete Note
     * Delete a note. Supports optimistic concurrency via If-Match.
     * @returns void
     * @throws ApiError
     */
    public static deleteNote({
        noteId,
        ifMatch,
    }: {
        noteId: string,
        ifMatch?: (string | null),
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            headers: {
                'if-match': ifMatch,
            },
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Get Note
     * Retrieve a single note by ID.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getNote({
        noteId,
    }: {
        noteId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
    /**
     * Update Note
     * Update a note (partial). Supports optimistic concurrency via If-Match.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateNote({
        noteId,
        requestBody,
        ifMatch,
    }: {
        noteId: string,
        requestBody: NoteUpdateRequest,
        ifMatch?: (string | null),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            headers: {
                'if-match': ifMatch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                401: `Unauthorized`,
                403: `Forbidden`,
                422: `Unprocessable Entity`,
                500: `Internal Server Error`,
                503: `Service Unavailable`,
            },
        });
    }
}
