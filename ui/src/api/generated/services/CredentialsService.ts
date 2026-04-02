/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectLinkRequest } from '../models/ConnectLinkRequest';
import type { CredentialCreate } from '../models/CredentialCreate';
import type { CredentialOut } from '../models/CredentialOut';
import type { CredentialPatch } from '../models/CredentialPatch';
import type { OAuthBrokerCreate } from '../models/OAuthBrokerCreate';
import type { OAuthBrokerOut } from '../models/OAuthBrokerOut';
import type { SyncRequest } from '../models/SyncRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CredentialsService {
    /**
     * Store an upstream API credential — add a secret to the vault for broker injection
     * Store an encrypted credential in the vault for automatic broker injection.
     *
     * Values are encrypted at rest and **never returned** after creation. Set `api_id` to
     * bind the credential to an API; the broker will inject it automatically when proxying
     * calls to that API.
     *
     * ---
     *
     * ### `auth_type` reference
     *
     * Set `auth_type` to tell the broker how to inject the credential into upstream requests.
     * Based on the [Postman auth type taxonomy](https://learning.postman.com/docs/sending-requests/authorization/authorization-types/).
     *
     * | `auth_type` | Status | Broker injects | `value` | `identity` |
     * |---|---|---|---|---|
     * | `bearer` | ✅ implemented | `Authorization: Bearer {value}` | Token, PAT, or OAuth access token | Not used |
     * | `basic` | ✅ implemented | `Authorization: Basic base64({identity\|"token"}:{value})` | Password or PAT | Username (optional — defaults to `"token"` if omitted, works for GitHub PATs) |
     * | `apiKey` | ✅ implemented | Custom header or query param `= {value}` | API key | For **compound schemes** (e.g. Discourse `Api-Key` + `Api-Username`): set `identity` to the username — one credential covers both headers when the overlay uses canonical `Secret`/`Identity` scheme names |
     * | `oauth2` | ⚠️ partial | `Authorization: Bearer {value}` — token must be pre-obtained | Access token (Pipedream-managed flows only via `pipedream_oauth`) | Not used |
     * | `digest` | 🔲 planned | RFC 2617 challenge-response (nonce/HMAC handshake) | Password | Username |
     * | `jwt` | 🔲 planned | `Authorization: Bearer {signed_jwt}` — auto-generated from signing key | Private key or secret | Key ID (`kid`) — signing algorithm and claims go in `context` |
     * | `aws_sig4` | 🔲 planned | `Authorization: AWS4-HMAC-SHA256 ...` signed headers | AWS Secret Access Key | AWS Access Key ID — region and service go in `context` |
     * | `oauth1` | 🔲 planned | HMAC-SHA1 signed request (nonce + timestamp) | OAuth secret | OAuth consumer key |
     * | `hawk` | 🔲 planned | `Authorization: Hawk ...` HMAC request signing | Hawk secret | Hawk key ID |
     * | `ntlm` | 🔲 not planned | Windows NTLM challenge-response | Password | Username + domain |
     * | `akamai_edgegrid` | 🔲 not planned | Akamai EdgeGrid signing | Client secret | Client token + access token in `context` |
     *
     * **Notes:**
     * - `pipedream_oauth` is a reserved value written by the Pipedream integration — do not set it manually.
     * - For `oauth2` full flows (auth code, client credentials, PKCE, token refresh) see the roadmap.
     * - `context` (not yet exposed) will hold auxiliary fields for multi-value schemes (JWT claims, AWS region/service, etc.).
     *
     * ---
     *
     * ### Workflow
     *
     * 1. Call `GET /apis/{api_id}` — check `security_schemes` and `credentials_configured` to find gaps.
     * 2. Post this endpoint with `api_id`, `auth_type`, `value` (and `identity` if needed).
     * 3. The broker injects the credential automatically on every proxied call to that API.
     * 4. To scope a credential to a specific toolkit: `POST /toolkits/{id}/credentials`.
     *
     * If the API has no registered security scheme yet, submit an overlay first: `POST /apis/{api_id}/overlays`.
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static createCredentialsPost({
        requestBody,
    }: {
        requestBody: CredentialCreate,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/credentials',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List upstream API credentials — labels and API bindings only, no secret values
     * List stored upstream API credentials. Values are never returned.
     *
     * All authenticated callers (agent keys and human sessions) can see all credential
     * labels and IDs — this is intentional. Labels are not secrets, and agents need
     * to discover credential IDs in order to file targeted `grant` access requests
     * (e.g. "bind Work Gmail" vs "bind Personal Gmail").
     *
     * Use `GET /credentials/{id}` to retrieve a specific credential by ID.
     * Filter with `?api_id=api.github.com` to list all credentials for a given API.
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static listCredentialsCredentialsGet({
        apiId,
    }: {
        apiId?: (string | null),
    }): CancelablePromise<Array<CredentialOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/credentials',
            query: {
                'api_id': apiId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get an upstream API credential by ID
     * Retrieve metadata for a single credential. Value is never returned.
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static getCredentialCredentialsCidGet({
        cid,
    }: {
        cid: string,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update an upstream API credential — rotate a secret or fix its API binding
     * @returns CredentialOut Successful Response
     * @throws ApiError
     */
    public static patchCredentialsCidPatch({
        cid,
        requestBody,
    }: {
        cid: string,
        requestBody: CredentialPatch,
    }): CancelablePromise<CredentialOut> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete an upstream API credential
     * @returns void
     * @throws ApiError
     */
    public static deleteCredentialsCidDelete({
        cid,
    }: {
        cid: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/credentials/{cid}',
            path: {
                'cid': cid,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List registered OAuth brokers
     * Return all registered OAuth brokers as a flat list. `client_secret` is never included.
     *
     * Accessible to both agents (toolkit key) and humans (session).
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listOauthBrokersOauthBrokersGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/oauth-brokers',
        });
    }
    /**
     * Register an OAuth broker
     * Register a delegated OAuth broker. Currently supported type: `pipedream`.
     *
     * ---
     *
     * ### Pipedream — one-time setup
     *
     * Before registering, complete these steps in the Pipedream UI:
     *
     * **1.** Go to [pipedream.com](https://pipedream.com) and sign in or create an account.
     *
     * **2.** Go to **Settings** (main menu) → **API** → click **+ New OAuth Client**.
     * Name it "Jentic". Store the **client ID** and **client secret** safely — the secret is not shown again.
     *
     * **3.** Go to **Projects** (main menu) and click **+ New Project**. Name it "Jentic".
     *
     * **4.** Go to **Projects → Jentic → Settings** and note the **project ID** (format: `proj_xxx`).
     *
     * That's it. Register the broker below — Jentic automatically configures the Connect
     * application name, support email, and logo in Pipedream on your behalf, so you don't
     * need to touch the Connect → Configuration screen manually.
     *
     * ---
     *
     * ### Registration
     *
     * ```json
     * {
         * "type": "pipedream",
         * "config": {
             * "client_id": "oa_abc123",
             * "client_secret": "pd_secret_xxxx",
             * "project_id": "proj_abc123",
             * "support_email": "support@example.com"
             * }
             * }
             * ```
             *
             * `support_email` is optional but recommended — it is displayed to end users in the
             * Pipedream OAuth consent UI.
             *
             * `client_secret` is write-only — Fernet-encrypted at rest, never returned.
             *
             * ---
             *
             * ### After registration
             *
             * Once registered, connect individual apps with `POST /oauth-brokers/{id}/connect-link`
             * (pass `app` as the Pipedream app slug, e.g. `gmail`, `google_calendar`, `slack`).
             * After the user completes OAuth, call `POST /oauth-brokers/{id}/sync` to pull the
             * connected account into Jentic. From that point, requests to that API's host are
             * automatically proxied with the user's OAuth token injected server-side.
             * @returns OAuthBrokerOut Successful Response
             * @throws ApiError
             */
            public static createOauthBrokerOauthBrokersPost({
                requestBody,
            }: {
                requestBody: OAuthBrokerCreate,
            }): CancelablePromise<OAuthBrokerOut> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/oauth-brokers',
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Get an OAuth broker
             * @returns any Successful Response
             * @throws ApiError
             */
            public static getOauthBrokerOauthBrokersBrokerIdGet({
                brokerId,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'GET',
                    url: '/oauth-brokers/{broker_id}',
                    path: {
                        'broker_id': brokerId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Remove an OAuth broker
             * Remove a broker and all its connected account mappings.
             *
             * Does not revoke tokens on the provider side — do that in the provider's dashboard.
             * @returns any Successful Response
             * @throws ApiError
             */
            public static deleteOauthBrokerOauthBrokersBrokerIdDelete({
                brokerId,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'DELETE',
                    url: '/oauth-brokers/{broker_id}',
                    path: {
                        'broker_id': brokerId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * List connected accounts for an OAuth broker
             * List the OAuth-connected account mappings stored for this broker.
             *
             * Each entry represents a SaaS app the user has connected via Pipedream's OAuth
             * UI, along with the API host it maps to and the Pipedream `account_id` used when
             * routing requests through the proxy.
             *
             * Use `POST /oauth-brokers/{id}/sync` to refresh this list from Pipedream.
             * @returns any Successful Response
             * @throws ApiError
             */
            public static listBrokerAccountsOauthBrokersBrokerIdAccountsGet({
                brokerId,
                externalUserId,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
                /**
                 * Filter by external user ID
                 */
                externalUserId?: (string | null),
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'GET',
                    url: '/oauth-brokers/{broker_id}/accounts',
                    path: {
                        'broker_id': brokerId,
                    },
                    query: {
                        'external_user_id': externalUserId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Generate a Pipedream Connect Link for authorising apps
             * Generate a short-lived Pipedream Connect Link URL.
             *
             * Visit the returned `connect_link_url` in a browser to authorise SaaS apps
             * (e.g. Gmail, Slack, GitHub) via Pipedream's hosted OAuth consent UI.
             *
             * After completing the OAuth flow, call `POST /oauth-brokers/{id}/sync` to
             * pull the new account into jentic-mini so requests start routing through it.
             *
             * The link expires after ~1 hour. Generate a new one if it expires before use.
             *
             * Intentionally open to agents (not human-session-only): only a human can
             * complete the OAuth flow, so generating the link is safe for agents to initiate.
             * Requires at minimum a valid toolkit key or trusted-subnet (admin) access.
             * @returns any Successful Response
             * @throws ApiError
             */
            public static createConnectLinkOauthBrokersBrokerIdConnectLinkPost({
                brokerId,
                requestBody,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
                requestBody: ConnectLinkRequest,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/oauth-brokers/{broker_id}/connect-link',
                    path: {
                        'broker_id': brokerId,
                    },
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Sync connected accounts from the OAuth broker
             * Re-fetch connected accounts from the provider and update local mappings.
             *
             * Call this after connecting a new app via Pipedream's hosted OAuth UI —
             * the new account will appear in subsequent `GET /oauth-brokers/{id}/accounts`
             * responses and the broker will start routing requests to it automatically.
             *
             * This does **not** affect accounts already connected — it is additive.
             *
             * Intentionally open to agents: syncing pulls in credentials the human already
             * authorised. No new OAuth flows are initiated.
             * @returns any Successful Response
             * @throws ApiError
             */
            public static syncBrokerAccountsOauthBrokersBrokerIdSyncPost({
                brokerId,
                requestBody,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
                requestBody: SyncRequest,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/oauth-brokers/{broker_id}/sync',
                    path: {
                        'broker_id': brokerId,
                    },
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Remove a connected account from an OAuth broker
             * Remove a specific connected account from this broker.
             *
             * This performs three actions in order:
             * 1. Revokes the account in the upstream provider (Pipedream) via their API
             * 2. Removes the associated credential from all toolkit provisioning
             * 3. Deletes the credential from the vault and the account from the local DB
             *
             * If the Pipedream revoke fails, the local cleanup still proceeds (with a warning).
             * @returns any Successful Response
             * @throws ApiError
             */
            public static deleteBrokerAccountOauthBrokersBrokerIdAccountsApiHostDelete({
                brokerId,
                apiHost,
                externalUserId,
            }: {
                /**
                 * The broker ID
                 */
                brokerId: string,
                apiHost: string,
                /**
                 * Filter by external user ID
                 */
                externalUserId?: (string | null),
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'DELETE',
                    url: '/oauth-brokers/{broker_id}/accounts/{api_host}',
                    path: {
                        'broker_id': brokerId,
                        'api_host': apiHost,
                    },
                    query: {
                        'external_user_id': externalUserId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
        }
