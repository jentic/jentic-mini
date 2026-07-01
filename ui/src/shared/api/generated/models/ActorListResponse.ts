/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActorSummaryResponse } from './ActorSummaryResponse';
/**
 * Paginated list of actors.
 */
export type ActorListResponse = {
    data: Array<ActorSummaryResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

