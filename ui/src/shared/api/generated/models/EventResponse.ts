/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EventLinks } from './EventLinks';
import type { EventSeverity } from './EventSeverity';
/**
 * Event representation in API responses.
 */
export type EventResponse = {
    _links: EventLinks;
    acknowledged: boolean;
    acknowledged_at?: (string | null);
    acknowledged_by?: (string | null);
    actor_id?: (string | null);
    actor_type?: (string | null);
    created_at: string;
    data?: Record<string, any>;
    detail?: (string | null);
    event_id: string;
    requires_action: boolean;
    severity: EventSeverity;
    summary: string;
    trace_id?: (string | null);
    type: string;
};

