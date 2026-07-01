/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EventResponse } from './EventResponse';
/**
 * Paginated list of events.
 */
export type EventListResponse = {
    data: Array<EventResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

