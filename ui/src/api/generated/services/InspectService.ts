/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InspectService {
    /**
     * Inspect a capability — get full schema, auth, and parameters before calling
     * Returns everything needed to call an operation or workflow: resolved parameter schema
     * (all $refs inlined), response schema, auth translated to concrete header instructions,
     * API context (name, description, tag descriptions), and HATEOAS _links (execute, upstream).
     *
     * Capability id format: METHOD/host/path — e.g. GET/api.stripe.com/v1/customers
     * or POST/{jentic_hostname}/workflows/summarise-latest-topics.
     * Pass ?toolkit_id=... to check whether credentials are configured for that toolkit.
     * Accept: text/markdown returns a compact LLM-friendly format.
     * Accept: application/openapi+yaml returns the raw OpenAPI operation snippet.
     * @returns any Full capability detail — format controlled by Accept header.
     * @throws ApiError
     */
    public static getCapabilityInspectCapabilityIdGet({
        capabilityId,
        toolkitId,
    }: {
        capabilityId: string,
        /**
         * Pass to include credential status for this toolkit
         */
        toolkitId?: (string | null),
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/inspect/{capability_id}',
            path: {
                'capability_id': capabilityId,
            },
            query: {
                'toolkit_id': toolkitId,
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
}
