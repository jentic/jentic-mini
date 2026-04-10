/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TraceOut } from './TraceOut';
/**
 * Paginated list of execution traces for auditing recent broker and workflow calls.
 */
export type TraceListPage = {
    /**
     * Total number of traces matching the query
     */
    total: number;
    /**
     * Maximum traces returned in this response
     */
    limit: number;
    /**
     * Starting offset for pagination (0-indexed)
     */
    offset: number;
    /**
     * Array of trace records for this page
     */
    traces: Array<TraceOut>;
};

