/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActorType } from './ActorType';
/**
 * Single actor entry in the actors list.
 */
export type ActorSummaryResponse = {
    active: boolean;
    actor_type: ActorType;
    created_at: string;
    id: string;
    name: string;
};

