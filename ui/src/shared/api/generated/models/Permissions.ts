/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EffectivePermission } from './EffectivePermission';
/**
 * Structured permissions view: assigned + effective.
 */
export type Permissions = {
    assigned: Array<string>;
    effective: Array<EffectivePermission>;
};

