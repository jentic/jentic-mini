/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PermissionRule } from './PermissionRule';
/**
 * Body for PATCH .../permissions — incremental rule updates.
 */
export type PermissionsPatch = {
    /**
     * Rules to append (deduplicated by exact match)
     */
    add?: Array<PermissionRule>;
    /**
     * Rules to remove by exact match
     */
    remove?: Array<PermissionRule>;
};

