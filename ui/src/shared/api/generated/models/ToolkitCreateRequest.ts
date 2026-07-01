/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { jentic_one__control__web__schemas__toolkits__PermissionRuleSchema } from './jentic_one__control__web__schemas__toolkits__PermissionRuleSchema';
/**
 * Create a new toolkit.
 */
export type ToolkitCreateRequest = {
    active?: boolean;
    credential_ids?: (Array<string> | null);
    description?: (string | null);
    name: string;
    permissions?: (Array<jentic_one__control__web__schemas__toolkits__PermissionRuleSchema> | null);
};

