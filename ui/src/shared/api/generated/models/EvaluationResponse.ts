/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EvaluationCheckResponse } from './EvaluationCheckResponse';
/**
 * Computed evaluation of whether the caller can fulfill a request.
 */
export type EvaluationResponse = {
    can_fulfill: boolean;
    checks: Array<EvaluationCheckResponse>;
};

