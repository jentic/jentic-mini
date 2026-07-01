/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PermissionListResponse } from '../models/PermissionListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PermissionsService {
    /**
     * List Permissions
     * List the permission catalogue visible to the caller.
     * @returns PermissionListResponse Successful Response
     * @throws ApiError
     */
    public static listPermissions(): CancelablePromise<PermissionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/permissions',
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
