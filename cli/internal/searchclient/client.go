// Package searchclient is a typed HTTP client for the Jentic registry search
// endpoint (POST /search). It supports lexical operation search with optional
// API filtering, pagination, and revision pinning.
package searchclient

import (
	"context"
	"errors"
	"net/http"
	"time"

	"github.com/jentic/jentic-one/cli/internal/httpx"
)

// ErrSearchUnsupported is returned when the server responds with HTTP 501,
// indicating that search is not enabled on this deployment.
var ErrSearchUnsupported = errors.New("search is not enabled on this deployment")

// Client talks to the Jentic registry search endpoint.
type Client struct {
	http *httpx.Client
}

// New returns a search client for the given base URL.
func New(baseURL string) *Client {
	return &Client{http: httpx.New(baseURL, 30*time.Second)}
}

// SearchRequest is the POST body for /search.
type SearchRequest struct {
	Query        string            `json:"query"`
	APIs         []string          `json:"apis,omitempty"`
	Limit        int               `json:"limit,omitempty"`
	Cursor       string            `json:"cursor,omitempty"`
	RevisionPins map[string]string `json:"revision_pins,omitempty"`
}

// SearchResult is the response envelope from /search.
type SearchResult struct {
	Data       []SearchHit `json:"data"`
	HasMore    bool        `json:"has_more"`
	NextCursor string      `json:"next_cursor"`
}

// APIRef is the API identity triple carried by each search hit, matching the
// server's ApiReferenceResponse (vendor/name/version plus derived host).
type APIRef struct {
	Vendor  string `json:"vendor"`
	Name    string `json:"name"`
	Version string `json:"version"`
	Host    string `json:"host"`
}

// String renders the API reference as the canonical vendor/name/version slug.
func (a APIRef) String() string {
	if a.Vendor == "" && a.Name == "" && a.Version == "" {
		return ""
	}
	return a.Vendor + "/" + a.Name + "/" + a.Version
}

// SearchLinks carries the hypermedia links for a search hit. inspect is the
// canonical, resolvable inspect identifier (?id=METHOD%20URL form) — prefer it
// over OperationID, which is the registry primary key and is namespace-distinct
// from the spec operationId surfaced elsewhere.
type SearchLinks struct {
	Inspect string `json:"inspect"`
}

// SearchHit is a single operation returned by the search endpoint. It mirrors
// the server's OperationResultResponse schema exactly; a drift here breaks
// decoding of every non-empty result page.
type SearchHit struct {
	Type        string      `json:"type"`
	API         APIRef      `json:"api"`
	OperationID string      `json:"operation_id"`
	Method      string      `json:"method"`
	URL         string      `json:"url"`
	Name        string      `json:"name"`
	Description string      `json:"description"`
	Score       float64     `json:"relevance_score"`
	Links       SearchLinks `json:"_links"`
}

// Search issues a POST /search and returns the result page. It maps HTTP 501
// to ErrSearchUnsupported for a friendly error message.
func (c *Client) Search(ctx context.Context, token string, req SearchRequest) (*SearchResult, error) {
	var out SearchResult
	if err := c.http.Do(ctx, http.MethodPost, "/search", token, req, &out); err != nil {
		var he *httpx.HTTPError
		if errors.As(err, &he) && he.StatusCode == http.StatusNotImplemented {
			return nil, ErrSearchUnsupported
		}
		return nil, err
	}
	return &out, nil
}
