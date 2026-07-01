/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreviewInfoResponse } from './PreviewInfoResponse';
import type { PreviewOperationResponse } from './PreviewOperationResponse';
/**
 * Capped, offset-paginated operation preview for a catalog entry.
 *
 * Unlike list endpoints (cursor-paginated), the preview uses simple
 * offset/limit pagination deliberately: it reads a single, already-fetched spec
 * document and is hard-capped at ``PREVIEW_MAX_OPERATIONS`` operations, so there
 * is no large/mutating result set that would justify keyset cursors.
 */
export type OperationPreviewListResponse = {
    /**
     * The page of previewed operations.
     */
    data: Array<PreviewOperationResponse>;
    /**
     * The spec's `info` block.
     */
    info: PreviewInfoResponse;
    /**
     * Offset of the returned window.
     */
    offset: number;
    /**
     * Slimmed `components.securitySchemes` projection.
     */
    security_schemes: Record<string, Record<string, any>>;
    /**
     * Total operations in the spec (pre-page).
     */
    total: number;
    /**
     * Whether more operations follow this window.
     */
    truncated: boolean;
};

