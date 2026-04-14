/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single import source for an OpenAPI spec or Arazzo workflow. Can be local file, URL, or inline content.
 */
export type ImportSource = {
    /**
     * Source type: 'path' (local file), 'url' (fetch from URL), or 'inline' (spec content in request)
     */
    type: string;
    /**
     * Local file system path (required if type='path')
     */
    path?: (string | null);
    /**
     * Remote spec URL (required if type='url')
     */
    url?: (string | null);
    /**
     * Override filename for saved spec (optional)
     */
    filename?: (string | null);
    /**
     * Inline spec content as JSON or YAML string (required if type='inline')
     */
    content?: (string | null);
    /**
     * Override derived API ID with catalog canonical ID (optional)
     */
    force_api_id?: (string | null);
};

