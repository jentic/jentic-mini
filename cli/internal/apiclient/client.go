// Package apiclient is a thin HTTP client for the Jentic control-plane local
// registry surface (the /apis tree plus /inspect): list/show imported APIs,
// list their revisions and operations, promote/archive/delete revisions, delete
// APIs, download specs, and inspect operations. It also fetches the public
// /openapi.json document (no token required). It targets the same control-plane
// base URL as authclient/catalogclient and attaches an agent bearer token to
// every authenticated request.
package apiclient

import (
	"context"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/jentic/jentic-one/cli/internal/httpx"
)

// Client talks to a single Jentic control-plane base URL.
type Client struct {
	http *httpx.Client
}

// New returns a client for the given base URL (trailing slash trimmed).
func New(baseURL string) *Client {
	return &Client{http: httpx.New(baseURL, 30*time.Second)}
}

// HTTPError is the shared problem-details transport error.
type HTTPError = httpx.HTTPError

// APIRef is the (vendor, name, version) identity triple plus derived host.
type APIRef struct {
	Vendor  string `json:"vendor"`
	Name    string `json:"name"`
	Version string `json:"version"`
	Host    string `json:"host"`
}

// API is a single locally registered API aggregate.
type API struct {
	API               APIRef   `json:"api"`
	DisplayName       string   `json:"display_name"`
	Description       string   `json:"description"`
	IconURL           string   `json:"icon_url"`
	CurrentRevisionID string   `json:"current_revision_id"`
	RevisionCount     int      `json:"revision_count"`
	OperationCount    int      `json:"operation_count"`
	SecuritySchemes   []string `json:"security_schemes"`
	CreatedAt         string   `json:"created_at"`
	UpdatedAt         string   `json:"updated_at"`
}

// APIList is a keyset page of locally registered APIs.
type APIList struct {
	Data       []API  `json:"data"`
	HasMore    bool   `json:"has_more"`
	NextCursor string `json:"next_cursor"`
}

// RevisionSource describes where a revision's spec came from.
type RevisionSource struct {
	Type        string `json:"type"`
	URL         string `json:"url"`
	Filename    string `json:"filename"`
	SubmittedBy string `json:"submitted_by"`
}

// Revision is a single revision of an API.
type Revision struct {
	RevisionID     string          `json:"revision_id"`
	API            APIRef          `json:"api"`
	Source         *RevisionSource `json:"source"`
	SpecDigest     string          `json:"spec_digest"`
	OperationCount int             `json:"operation_count"`
	SubmittedBy    string          `json:"submitted_by"`
	State          string          `json:"state"`
	IsCurrent      bool            `json:"is_current"`
	PromotedAt     string          `json:"promoted_at"`
	ArchivedAt     string          `json:"archived_at"`
	CreatedAt      string          `json:"created_at"`
}

// RevisionList is a keyset page of revisions.
type RevisionList struct {
	Data       []Revision `json:"data"`
	HasMore    bool       `json:"has_more"`
	NextCursor string     `json:"next_cursor"`
}

// Operation is a single operation summary in a revision.
type Operation struct {
	OperationID string   `json:"operation_id"`
	Method      string   `json:"method"`
	Path        string   `json:"path"`
	API         APIRef   `json:"api"`
	RevisionID  string   `json:"revision_id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Tags        []string `json:"tags"`
	Deprecated  bool     `json:"deprecated"`
}

// OperationList is a keyset page of operations.
type OperationList struct {
	Data       []Operation `json:"data"`
	HasMore    bool        `json:"has_more"`
	NextCursor string      `json:"next_cursor"`
}

// ListParams holds the query options for List.
type ListParams struct {
	Vendor string
	Cursor string
	Limit  int
}

// List returns a keyset page of locally registered APIs.
func (c *Client) List(ctx context.Context, token string, p ListParams) (*APIList, error) {
	q := url.Values{}
	if p.Vendor != "" {
		q.Set("vendor", p.Vendor)
	}
	if p.Cursor != "" {
		q.Set("cursor", p.Cursor)
	}
	if p.Limit > 0 {
		q.Set("limit", strconv.Itoa(p.Limit))
	}
	path := "/apis"
	if len(q) > 0 {
		path += "?" + q.Encode()
	}
	var out APIList
	if err := c.http.Do(ctx, http.MethodGet, path, token, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Get resolves a single API by its (vendor, name, version) identity.
func (c *Client) Get(ctx context.Context, token, vendor, name, version string) (*API, error) {
	var out API
	if err := c.http.Do(ctx, http.MethodGet, apiPath(vendor, name, version, ""), token, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// RevisionParams holds the query options for Revisions.
type RevisionParams struct {
	States []string
	Cursor string
	Limit  int
}

// Revisions lists the revisions of an API.
func (c *Client) Revisions(ctx context.Context, token, vendor, name, version string, p RevisionParams) (*RevisionList, error) {
	q := url.Values{}
	for _, s := range p.States {
		if s != "" {
			q.Add("state", s)
		}
	}
	if p.Cursor != "" {
		q.Set("cursor", p.Cursor)
	}
	if p.Limit > 0 {
		q.Set("limit", strconv.Itoa(p.Limit))
	}
	var out RevisionList
	if err := c.http.Do(ctx, http.MethodGet, apiPath(vendor, name, version, "/revisions")+httpx.Query(q), token, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Operations lists the operations of an API. When revisionID is empty, the
// API's current (live) revision is used; otherwise the named revision.
func (c *Client) Operations(ctx context.Context, token, vendor, name, version, revisionID string, cursor string, limit int) (*OperationList, error) {
	q := url.Values{}
	if cursor != "" {
		q.Set("cursor", cursor)
	}
	if limit > 0 {
		q.Set("limit", strconv.Itoa(limit))
	}
	suffix := "/operations"
	if revisionID != "" {
		suffix = "/revisions/" + url.PathEscape(revisionID) + "/operations"
	}
	var out OperationList
	if err := c.http.Do(ctx, http.MethodGet, apiPath(vendor, name, version, suffix)+httpx.Query(q), token, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Promote publishes a draft revision (archiving the current one).
func (c *Client) Promote(ctx context.Context, token, vendor, name, version, revisionID string) error {
	suffix := "/revisions/" + url.PathEscape(revisionID) + ":promote"
	return c.http.Do(ctx, http.MethodPost, apiPath(vendor, name, version, suffix), token, nil, nil)
}

// Archive archives a draft revision.
func (c *Client) Archive(ctx context.Context, token, vendor, name, version, revisionID string) error {
	suffix := "/revisions/" + url.PathEscape(revisionID) + ":archive"
	return c.http.Do(ctx, http.MethodPost, apiPath(vendor, name, version, suffix), token, nil, nil)
}

// DeleteAPI deletes an API and all of its revisions.
func (c *Client) DeleteAPI(ctx context.Context, token, vendor, name, version string) error {
	return c.http.Do(ctx, http.MethodDelete, apiPath(vendor, name, version, ""), token, nil, nil)
}

// DeleteRevision deletes an archived revision.
func (c *Client) DeleteRevision(ctx context.Context, token, vendor, name, version, revisionID string) error {
	suffix := "/revisions/" + url.PathEscape(revisionID)
	return c.http.Do(ctx, http.MethodDelete, apiPath(vendor, name, version, suffix), token, nil, nil)
}

// Spec downloads the OpenAPI document for an API's current (live) revision, or
// a specific revision when revisionID is set. When yaml is true the body is
// requested (and returned) as YAML; otherwise JSON. The raw bytes are returned.
func (c *Client) Spec(ctx context.Context, token, vendor, name, version, revisionID string, yaml bool) ([]byte, error) {
	suffix := "/openapi"
	if revisionID != "" {
		suffix = "/revisions/" + url.PathEscape(revisionID) + "/openapi"
	}
	accept := "application/json"
	if yaml {
		accept = "application/yaml"
	}
	return c.http.DoRaw(ctx, http.MethodGet, apiPath(vendor, name, version, suffix), token, accept)
}

// Inspect resolves an operation to structural detail. format is one of
// "json", "markdown", or "openapi"; the raw negotiated body is returned.
func (c *Client) Inspect(ctx context.Context, token, operationID, revisionID, format string) ([]byte, error) {
	q := url.Values{}
	if method, target, ok := parseMethodURL(operationID); ok {
		q.Set("id", method+" "+target)
	} else {
		q.Set("operation_id", operationID)
	}
	if revisionID != "" {
		q.Set("revision_id", revisionID)
	}
	accept := inspectAccept(format)
	return c.http.DoRaw(ctx, http.MethodGet, "/inspect"+httpx.Query(q), token, accept)
}

// parseMethodURL detects the "METHOD URL" identifier form (as printed by
// `jentic search`) and splits it into its parts. Both "GET https://host/p" and
// "GET:https://host/p" are accepted. It returns ok=false for an opaque
// operation ID. The server's /inspect endpoint resolves "METHOD URL" via the
// id= query param and opaque IDs via operation_id=.
func parseMethodURL(s string) (method, target string, ok bool) {
	s = strings.TrimSpace(s)
	var first, rest string
	if sp, r, found := strings.Cut(s, " "); found {
		first, rest = sp, r
	} else if c, r, found := strings.Cut(s, ":"); found {
		first, rest = c, r
	} else {
		return "", "", false
	}
	rest = strings.TrimSpace(rest)
	if !strings.HasPrefix(rest, "http://") && !strings.HasPrefix(rest, "https://") {
		return "", "", false
	}
	switch strings.ToUpper(first) {
	case "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS":
		return strings.ToUpper(first), rest, true
	default:
		return "", "", false
	}
}

func inspectAccept(format string) string {
	switch format {
	case "markdown", "md":
		return "text/markdown"
	case "openapi", "yaml":
		return "application/openapi+yaml"
	default:
		return "application/json"
	}
}

// Reference fetches the public endpoint + scope reference
// (/reference/endpoints.json). This is the canonical machine-readable join of
// every endpoint with its scope(s), actor types, and typical-caller hint —
// served from the same builder that writes docs/reference/endpoints.json, so the
// CLI never parses authorization out of the OpenAPI document. No token required.
func (c *Client) Reference(ctx context.Context) ([]byte, error) {
	return c.http.DoRaw(ctx, http.MethodGet, "/reference/endpoints.json", "", "application/json")
}

// apiPath builds a /apis/{vendor}/{name}/{version}{suffix} path with each
// identity segment percent-escaped (local API identities never contain
// slashes, unlike catalog api_id values).
func apiPath(vendor, name, version, suffix string) string {
	return "/apis/" + url.PathEscape(vendor) + "/" + url.PathEscape(name) + "/" +
		url.PathEscape(version) + suffix
}
