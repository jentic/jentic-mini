/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccessRequestBody } from '../models/AccessRequestBody';
import type { AccessRequestOut } from '../models/AccessRequestOut';
import type { CredentialBindingOut } from '../models/CredentialBindingOut';
import type { KeyCreate } from '../models/KeyCreate';
import type { PermissionRule } from '../models/PermissionRule';
import type { PermissionsPatch } from '../models/PermissionsPatch';
import type { ToolkitCreate } from '../models/ToolkitCreate';
import type { ToolkitCredentialAdd } from '../models/ToolkitCredentialAdd';
import type { ToolkitKeyCreated } from '../models/ToolkitKeyCreated';
import type { ToolkitKeyOut } from '../models/ToolkitKeyOut';
import type { ToolkitOut } from '../models/ToolkitOut';
import type { ToolkitPatch } from '../models/ToolkitPatch';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ToolkitsService {
    /**
     * List toolkits
     * List all toolkits.
     * @returns ToolkitOut Successful Response
     * @throws ApiError
     */
    public static listToolkitsToolkitsGet(): CancelablePromise<Array<ToolkitOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits',
        });
    }
    /**
     * Create a toolkit — scoped bundle of upstream API credentials with a client API key
     * Creates a toolkit: a named bundle of upstream API credentials with a scoped client API key for the agent.
     * Returns a toolkit API key (col_xxx) — shown once, not recoverable.
     * Bind credentials via POST /toolkits/{id}/credentials.
     * Set access policy via PUT /toolkits/{id}/credentials/{cred_id}/permissions.
     * Agents use toolkit keys to call the broker; only bound credentials are injected.
     * @returns ToolkitOut Successful Response
     * @throws ApiError
     */
    public static createToolkitToolkitsPost({
        requestBody,
    }: {
        requestBody: ToolkitCreate,
    }): CancelablePromise<ToolkitOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get toolkit — metadata, bound upstream API credentials, client API keys, and policy summary
     * Get toolkit with all inline context: metadata, bound upstream API credentials, client API key count, and policy summary.
     * The default toolkit implicitly contains ALL upstream API credentials — no explicit binding needed.
     * @returns ToolkitOut Successful Response
     * @throws ApiError
     */
    public static getToolkitToolkitsToolkitIdGet({
        toolkitId,
    }: {
        toolkitId: string,
    }): CancelablePromise<ToolkitOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}',
            path: {
                'toolkit_id': toolkitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update toolkit — rename or update description
     * @returns ToolkitOut Successful Response
     * @throws ApiError
     */
    public static patchToolkitToolkitsToolkitIdPatch({
        toolkitId,
        requestBody,
    }: {
        toolkitId: string,
        requestBody: ToolkitPatch,
    }): CancelablePromise<ToolkitOut> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/toolkits/{toolkit_id}',
            path: {
                'toolkit_id': toolkitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete toolkit and revoke all its client API keys
     * @returns void
     * @throws ApiError
     */
    public static deleteToolkitToolkitsToolkitIdDelete({
        toolkitId,
    }: {
        toolkitId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/toolkits/{toolkit_id}',
            path: {
                'toolkit_id': toolkitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Issue a new client API key for this toolkit
     * Issues an additional client API key (tk_xxx) for this toolkit. Hand this key to the agent. Optionally restrict by IP (CIDR list). Returned once — not recoverable.
     * @returns ToolkitKeyCreated Successful Response
     * @throws ApiError
     */
    public static createToolkitKeyToolkitsToolkitIdKeysPost({
        toolkitId,
        requestBody,
    }: {
        toolkitId: string,
        requestBody: KeyCreate,
    }): CancelablePromise<ToolkitKeyCreated> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/keys',
            path: {
                'toolkit_id': toolkitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List client API keys for this toolkit — metadata only, no secret values
     * List all access keys for this toolkit.
     *
     * Active and revoked keys are shown (revoked keys have `revoked_at` set).
     * The `api_key` value is never returned — only the key ID and metadata.
     * @returns ToolkitKeyOut Successful Response
     * @throws ApiError
     */
    public static listToolkitKeysToolkitsToolkitIdKeysGet({
        toolkitId,
    }: {
        toolkitId: string,
    }): CancelablePromise<Array<ToolkitKeyOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/keys',
            path: {
                'toolkit_id': toolkitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update a client API key — rename or change IP restrictions
     * Update label or IP restrictions on a client API key. Cannot change the key value itself.
     * @returns ToolkitKeyOut Successful Response
     * @throws ApiError
     */
    public static patchToolkitKeyToolkitsToolkitIdKeysKeyIdPatch({
        toolkitId,
        keyId,
        requestBody,
    }: {
        toolkitId: string,
        keyId: string,
        requestBody: KeyCreate,
    }): CancelablePromise<ToolkitKeyOut> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/toolkits/{toolkit_id}/keys/{key_id}',
            path: {
                'toolkit_id': toolkitId,
                'key_id': keyId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revoke a client API key
     * Revoke a single access key.
     *
     * Other keys for this toolkit remain active. The revoked key immediately
     * stops working — any agent using it will receive 401 on their next request.
     * @returns void
     * @throws ApiError
     */
    public static revokeToolkitKeyToolkitsToolkitIdKeysKeyIdDelete({
        toolkitId,
        keyId,
    }: {
        toolkitId: string,
        keyId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/toolkits/{toolkit_id}/keys/{key_id}',
            path: {
                'toolkit_id': toolkitId,
                'key_id': keyId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Bind an upstream API credential to this toolkit — enable broker injection
     * Enrolls an existing upstream API credential in this toolkit. The broker automatically injects it into outbound calls for the API it's bound to, when the agent calls using this toolkit's client API key.
     * @returns CredentialBindingOut Successful Response
     * @throws ApiError
     */
    public static addCredentialToToolkitToolkitsToolkitIdCredentialsPost({
        toolkitId,
        requestBody,
    }: {
        toolkitId: string,
        requestBody: ToolkitCredentialAdd,
    }): CancelablePromise<CredentialBindingOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/credentials',
            path: {
                'toolkit_id': toolkitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List upstream API credentials bound to this toolkit
     * List upstream API credentials bound to this toolkit. Admin key only.
     * @returns CredentialBindingOut Successful Response
     * @throws ApiError
     */
    public static listToolkitCredentialsToolkitsToolkitIdCredentialsGet({
        toolkitId,
    }: {
        toolkitId: string,
    }): CancelablePromise<Array<CredentialBindingOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/credentials',
            path: {
                'toolkit_id': toolkitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Unbind an upstream API credential from this toolkit
     * @returns void
     * @throws ApiError
     */
    public static removeCredentialFromToolkitToolkitsToolkitIdCredentialsCredentialIdDelete({
        toolkitId,
        credentialId,
    }: {
        toolkitId: string,
        credentialId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/toolkits/{toolkit_id}/credentials/{credential_id}',
            path: {
                'toolkit_id': toolkitId,
                'credential_id': credentialId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get the permission rules for a specific credential in this toolkit
     * Returns all rules in evaluation order for this credential: agent-defined rules first,
     * then the immutable system safety rules appended by the server. First match wins.
     *
     * Since rules are scoped to a single credential (which is bound to a specific API),
     * path and operation patterns apply only to calls made using this credential.
     * System rules are tagged `_system: true` — they cannot be removed.
     * @returns PermissionRule Successful Response
     * @throws ApiError
     */
    public static getCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsGet({
        toolkitId,
        credId,
    }: {
        toolkitId: string,
        credId: string,
    }): CancelablePromise<Array<PermissionRule>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/credentials/{cred_id}/permissions',
            path: {
                'toolkit_id': toolkitId,
                'cred_id': credId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Replace permission rules for a specific credential
     * Replaces the entire agent rule list for this credential.
     * System safety rules are always appended server-side and cannot be removed.
     * Use `PATCH` to add or remove individual rules without replacing the full list.
     * @returns PermissionRule Successful Response
     * @throws ApiError
     */
    public static setCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPut({
        toolkitId,
        credId,
        requestBody,
    }: {
        toolkitId: string,
        credId: string,
        requestBody: Array<PermissionRule>,
    }): CancelablePromise<Array<PermissionRule>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/toolkits/{toolkit_id}/credentials/{cred_id}/permissions',
            path: {
                'toolkit_id': toolkitId,
                'cred_id': credId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add or remove individual permission rules for a specific credential
     * Incrementally update rules for this credential without replacing the full list.
     *
     * - `add`: rules appended (deduplicated)
     * - `remove`: rules removed by exact match
     *
     * Example — unlock TTS writes for this credential:
     * ```json
     * {"add": [{"effect": "allow", "methods": ["POST"], "path": "text-to-speech"}]}
     * ```
     * @returns PermissionRule Successful Response
     * @throws ApiError
     */
    public static patchCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPatch({
        toolkitId,
        credId,
        requestBody,
    }: {
        toolkitId: string,
        credId: string,
        requestBody: PermissionsPatch,
    }): CancelablePromise<Array<PermissionRule>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/toolkits/{toolkit_id}/credentials/{cred_id}/permissions',
            path: {
                'toolkit_id': toolkitId,
                'cred_id': credId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Request access — ask a human to grant a credential or adjust permissions
     * Agent submits an access request. A human approves or denies it at the `approve_url`.
     *
     * **Workflow:**
     * 1. `GET /credentials?api_id=<host>` — find the `credential_id` you need
     * 2. `POST` this endpoint with `type`, `credential_id`, `rules`, and optional `reason`
     * 3. Return the `approve_url` to your user and poll `status` until `approved` or `denied`
     *
     * The toolkit ID in the URL must match the caller's own toolkit.
     * Admin/human sessions may file requests on behalf of any toolkit.
     * @returns AccessRequestOut Successful Response
     * @throws ApiError
     */
    public static createAccessRequestToolkitsToolkitIdAccessRequestsPost({
        toolkitId,
        requestBody,
    }: {
        toolkitId: string,
        requestBody: AccessRequestBody,
    }): CancelablePromise<AccessRequestOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/access-requests',
            path: {
                'toolkit_id': toolkitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List access requests for this toolkit
     * List access requests for a toolkit, newest first.
     *
     * Each item includes the full `payload` (credential ID, rules, etc.) and current `status`.
     * Filter by `status=pending` to find outstanding requests awaiting approval.
     *
     * **`type` values:**
     * - `grant` — agent is requesting a new credential be bound; `payload` contains `credential_id` and optional `rules`
     * - `modify_permissions` — agent is requesting a rule change on an existing credential; `payload` contains `credential_id` and `rules`
     *
     * Agent keys see only their own toolkit's requests. Admin/human sessions may view any toolkit.
     * @returns AccessRequestOut Successful Response
     * @throws ApiError
     */
    public static listAccessRequestsToolkitsToolkitIdAccessRequestsGet({
        toolkitId,
        status,
    }: {
        toolkitId: string,
        status?: (string | null),
    }): CancelablePromise<Array<AccessRequestOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/access-requests',
            path: {
                'toolkit_id': toolkitId,
            },
            query: {
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Poll an access request — check approval status
     * Poll the status of a specific access request.
     *
     * Poll this endpoint after directing the user to `approve_url`. Status transitions:
     * `pending` → `approved` | `denied`
     *
     * On approval, the `payload` contains the exact data that was applied (credential bound,
     * rules set, etc.). For programmatic polling, check `status` field only — `approved`
     * means the side effects have already been applied and the toolkit is ready to use.
     * @returns AccessRequestOut Successful Response
     * @throws ApiError
     */
    public static getAccessRequestToolkitsToolkitIdAccessRequestsReqIdGet({
        toolkitId,
        reqId,
    }: {
        toolkitId: string,
        reqId: string,
    }): CancelablePromise<AccessRequestOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/toolkits/{toolkit_id}/access-requests/{req_id}',
            path: {
                'toolkit_id': toolkitId,
                'req_id': reqId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Approve an access request (human session only)
     * Approve a pending access request (human or admin action — agent keys cannot do this).
     *
     * For `grant` requests: the upstream API credential is automatically bound to the toolkit.
     * For `modify_permissions` requests: the new permission rules are applied immediately.
     * @returns AccessRequestOut Successful Response
     * @throws ApiError
     */
    public static approveAccessRequestToolkitsToolkitIdAccessRequestsReqIdApprovePost({
        toolkitId,
        reqId,
    }: {
        toolkitId: string,
        reqId: string,
    }): CancelablePromise<AccessRequestOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/access-requests/{req_id}/approve',
            path: {
                'toolkit_id': toolkitId,
                'req_id': reqId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Deny an access request (human session only)
     * Deny a pending access request.
     * @returns AccessRequestOut Successful Response
     * @throws ApiError
     */
    public static denyAccessRequestToolkitsToolkitIdAccessRequestsReqIdDenyPost({
        toolkitId,
        reqId,
    }: {
        toolkitId: string,
        reqId: string,
    }): CancelablePromise<AccessRequestOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/toolkits/{toolkit_id}/access-requests/{req_id}/deny',
            path: {
                'toolkit_id': toolkitId,
                'req_id': reqId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
