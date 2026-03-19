/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiListPage } from '../models/ApiListPage';
import type { ApiOut } from '../models/ApiOut';
import type { ImportOut } from '../models/ImportOut';
import type { ImportRequest } from '../models/ImportRequest';
import type { NoteCreate } from '../models/NoteCreate';
import type { OperationListPage } from '../models/OperationListPage';
import type { OverlaySubmit } from '../models/OverlaySubmit';
import type { SchemeInput } from '../models/SchemeInput';
import type { WorkflowOut } from '../models/WorkflowOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CatalogService {
    /**
     * List workflows — browse available multi-step Arazzo workflows
     * Returns all registered workflows with slug, name, description, step count, and involved APIs. Use GET /inspect/{id} or GET /workflows/{slug} for full detail.
     * @returns WorkflowOut Successful Response
     * @throws ApiError
     */
    public static listWorkflowsWorkflowsGet(): CancelablePromise<Array<WorkflowOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/workflows',
        });
    }
    /**
     * Get workflow definition — Arazzo spec and input schema
     * Returns the workflow definition with content negotiation:
     * - application/json (default): Arazzo document
     * - text/markdown: compact LLM-friendly summary with input schema and steps
     * - text/html: human-readable summary
     * - application/arazzo+json: same as application/json
     * Execute via broker: POST /{jentic_host}/workflows/{slug}
     * @returns any Workflow definition — format controlled by Accept header.
     * @throws ApiError
     */
    public static getWorkflowWorkflowsSlugGet({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/workflows/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Import an API spec or workflow — add to the searchable catalog
     * Registers an OpenAPI spec or Arazzo workflow into the catalog and BM25 index.
     * Source types: url (fetch from URL), upload (multipart file), inline (JSON body).
     * For OpenAPI specs: parses operations, computes capability IDs, indexes descriptions.
     * For Arazzo workflows: stores definition, extracts input schema and involved APIs.
     * Returns the registered API or workflow with its canonical id.
     * @returns ImportOut Successful Response
     * @throws ApiError
     */
    public static importSourcesImportPost({
        requestBody,
    }: {
        requestBody: ImportRequest,
    }): CancelablePromise<ImportOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/import',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Browse the Jentic public API catalog
     * Browse and search the public Jentic API catalog (jentic/jentic-public-apis).
     *
     * Returns individual APIs including expanded sub-APIs for umbrella vendors
     * (e.g. googleapis.com/gmail, googleapis.com/calendar, atlassian.com/jira).
     * Results show `registered: true/false` to distinguish APIs already in your local
     * registry from those available to use.
     *
     * To use a catalog API: call `POST /credentials` with its `api_id` — the spec
     * is imported automatically. Manifest is auto-refreshed daily; force a refresh
     * via `POST /catalog/refresh`.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listCatalogCatalogGet({
        q,
        limit = 50,
        registeredOnly = false,
        unregisteredOnly = false,
    }: {
        /**
         * Filter by API name/domain, e.g. "stripe" or "slack"
         */
        q?: (string | null),
        /**
         * Max results
         */
        limit?: number,
        /**
         * Only show APIs already imported into your registry
         */
        registeredOnly?: boolean,
        /**
         * Only show APIs not yet in your registry
         */
        unregisteredOnly?: boolean,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/catalog',
            query: {
                'q': q,
                'limit': limit,
                'registered_only': registeredOnly,
                'unregistered_only': unregisteredOnly,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh the catalog manifest from GitHub
     * Fetches the full recursive git tree from jentic/jentic-public-apis and builds
     * a detailed manifest that correctly identifies individual APIs within umbrella vendors
     * (e.g. googleapis.com expands to googleapis.com/gmail, googleapis.com/calendar, etc.).
     *
     * Takes ~2-5 seconds (two unauthenticated GitHub API calls). Safe to call repeatedly.
     * Falls back to a shallow top-level listing if the tree response is truncated.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static refreshCatalogCatalogRefreshPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/catalog/refresh',
        });
    }
    /**
     * Inspect a catalog entry
     * Inspect a single catalog API entry. Shows registration status, GitHub link,
     * and available spec files (fetched live from GitHub).
     *
     * Note: this makes a live GitHub API call to list the directory contents.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCatalogEntryCatalogApiIdGet({
        apiId,
    }: {
        apiId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/catalog/{api_id}',
            path: {
                'api_id': apiId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Declare auth scheme — teach Jentic how to authenticate with this API
     * Registers a security scheme for an API that has missing or incorrect auth in its spec.
     * Generates an OpenAPI overlay stored as pending; auto-confirmed when broker gets a 2xx.
     * Supports: apiKey (header/query/cookie), bearer token, HTTP basic, OAuth2 client credentials, multiple headers.
     * Returns generated_overlay, scheme_names, and next_steps for credential registration.
     * Use this when the broker returns 'no security scheme found' for an API.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static submitSchemeApisApiIdSchemePost({
        apiId,
        requestBody,
    }: {
        apiId: string,
        requestBody: (SchemeInput | Array<SchemeInput>),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/apis/{api_id}/scheme',
            path: {
                'api_id': apiId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit raw OpenAPI overlay — patch the spec directly
     * Submit a raw OpenAPI overlay JSON to patch the stored spec for this API. Stored as pending; auto-confirmed on first successful broker call. Prefer POST /apis/{api_id}/scheme for structured auth registration.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static submitOverlayApisApiIdOverlaysPost({
        apiId,
        requestBody,
    }: {
        apiId: string,
        requestBody: OverlaySubmit,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/apis/{api_id}/overlays',
            path: {
                'api_id': apiId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List overlays for an API
     * List all overlays for an API.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listOverlaysApisApiIdOverlaysGet({
        apiId,
    }: {
        apiId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{api_id}/overlays',
            path: {
                'api_id': apiId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Overlay
     * Get a specific overlay including its full document.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getOverlayApisApiIdOverlaysOverlayIdGet({
        apiId,
        overlayId,
    }: {
        apiId: string,
        overlayId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{api_id}/overlays/{overlay_id}',
            path: {
                'api_id': apiId,
                'overlay_id': overlayId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List APIs — browse all available API providers (local and catalog)
     * Returns paginated list of API providers — both locally registered and from the Jentic public catalog.
     *
     * Every entry has:
     * - `source: "local"` — spec is indexed locally, operations are searchable and executable
     * - `source: "catalog"` — available from the Jentic public catalog; add credentials to use
     * - `has_credentials: bool` — whether credentials have been configured for this API
     *
     * Use `?source=local` or `?source=catalog` to filter. Default returns all.
     * To use a catalog API: call `POST /credentials` with `api_id` set — the spec is imported automatically.
     * @returns ApiListPage Successful Response
     * @throws ApiError
     */
    public static listApisApisGet({
        page = 1,
        limit = 20,
        source,
        q,
    }: {
        /**
         * Page number (1-indexed)
         */
        page?: number,
        /**
         * Results per page
         */
        limit?: number,
        /**
         * Filter by source: `local` (locally registered) or `catalog` (public catalog, not yet configured). Default: all.
         */
        source?: (string | null),
        /**
         * Substring filter on API id/name
         */
        q?: (string | null),
    }): CancelablePromise<ApiListPage> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis',
            query: {
                'page': page,
                'limit': limit,
                'source': source,
                'q': q,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List operations for an API — enumerate all available actions
     * Returns paginated list of operations for the given API. Each item has capability id, summary, and description. Use GET /inspect/{id} for full schema.
     * @returns OperationListPage Successful Response
     * @throws ApiError
     */
    public static listApiOperationsApisApiIdOperationsGet({
        apiId,
        page = 1,
        limit = 50,
    }: {
        apiId: string,
        /**
         * Page number (1-indexed)
         */
        page?: number,
        /**
         * Results per page
         */
        limit?: number,
    }): CancelablePromise<OperationListPage> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{api_id}/operations',
            path: {
                'api_id': apiId,
            },
            query: {
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get API summary — name, version, description, and stats
     * Returns API metadata: title, version, description, base URL, vendor, and total operation count. Use GET /apis/{api_id}/operations to enumerate operations.
     * @returns ApiOut Successful Response
     * @throws ApiError
     */
    public static getApiApisApiIdGet({
        apiId,
    }: {
        apiId: string,
    }): CancelablePromise<ApiOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/apis/{api_id}',
            path: {
                'api_id': apiId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add a note — annotate a capability with feedback or a correction
     * Attaches a note to any capability (operation, workflow, or API). Use to report auth corrections, schema errors, or updated Arazzo workflows. Notes feed back into the catalog improvement loop.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createNoteNotesPost({
        requestBody,
    }: {
        requestBody: NoteCreate,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/notes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List notes for a resource
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listNotesNotesGet({
        resource,
        type,
        limit = 50,
    }: {
        resource?: (string | null),
        type?: (string | null),
        limit?: number,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/notes',
            query: {
                'resource': resource,
                'type': type,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a note
     * @returns void
     * @throws ApiError
     */
    public static deleteNoteNotesNoteIdDelete({
        noteId,
    }: {
        noteId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
