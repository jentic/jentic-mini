/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JobListPage } from '../models/JobListPage';
import type { JobOut } from '../models/JobOut';
import type { TraceListPage } from '../models/TraceListPage';
import type { TraceOut } from '../models/TraceOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ObserveService {
    /**
     * List async jobs — paginated handles for outstanding and completed async calls
     * Returns async jobs only — calls that could not complete synchronously. Sync calls produce traces but no jobs. Filter by `status` (pending|running|complete|failed|upstream_async). Poll `GET /jobs/{id}` for individual job status.
     * @returns JobListPage Successful Response
     * @throws ApiError
     */
    public static listJobsJobsGet({
        status,
        page = 1,
        limit = 20,
    }: {
        /**
         * Filter by status
         */
        status?: (string | null),
        page?: number,
        limit?: number,
    }): CancelablePromise<JobListPage> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jobs',
            query: {
                'status': status,
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Poll async job — check status and retrieve result when complete
     * Poll this endpoint after receiving a 202. The job_id comes from the `Location` response header (RFC 7240) or the `X-Jentic-Job-Id` header. Returns `status: pending|running` while in progress. Returns `status: complete` with `result` when done. Returns `status: upstream_async` when the upstream API itself returned 202 — check `upstream_job_url` to follow the upstream job. Returns `status: failed` with `error` and `http_status` on failure.
     * @returns JobOut Successful Response
     * @throws ApiError
     */
    public static getJobRouteJobsJobIdGet({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<JobOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel async job — best-effort cancellation of an outstanding job
     * Requests cancellation of a pending or running async job. Best-effort: cancellation fires at the next async checkpoint; an in-flight upstream HTTP request will complete before the job stops. The job record is retained (marked failed, error='Cancelled by client'). Has no effect on already-completed jobs.
     * @returns void
     * @throws ApiError
     */
    public static cancelJobJobsJobIdDelete({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List execution traces — audit recent broker and workflow calls
     * Returns recent execution traces with status, capability id, toolkit, timestamp, and HTTP status. Use GET /traces/{trace_id} for step-level detail.
     * @returns TraceListPage Successful Response
     * @throws ApiError
     */
    public static listTracesTracesGet({
        limit = 20,
        offset,
    }: {
        limit?: number,
        offset?: number,
    }): CancelablePromise<TraceListPage> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/traces',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get trace detail — step-by-step execution log
     * Returns the full execution trace with all steps: capability called, inputs, outputs, HTTP status, and timing. Useful for debugging failed workflow steps.
     * @returns TraceOut Successful Response
     * @throws ApiError
     */
    public static getTraceTracesTraceIdGet({
        traceId,
    }: {
        traceId: string,
    }): CancelablePromise<TraceOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/traces/{trace_id}',
            path: {
                'trace_id': traceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
