/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single item decision.
 */
export type DecideItemSchema = {
    decision: DecideItemSchema.decision;
    decision_reason?: (string | null);
    item_id: string;
};
export namespace DecideItemSchema {
    export enum decision {
        APPROVED = 'approved',
        DENIED = 'denied',
    }
}

