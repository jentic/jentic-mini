/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Update toolkit metadata or toggle disabled/simulate flags. Only provided fields are changed.
 */
export type ToolkitPatch = {
    /**
     * New toolkit name (optional)
     */
    name?: (string | null);
    /**
     * New description (optional)
     */
    description?: (string | null);
    /**
     * Toggle dry-run mode (optional)
     */
    simulate?: (boolean | null);
    /**
     * Toggle toolkit disabled state (optional)
     */
    disabled?: (boolean | null);
};

