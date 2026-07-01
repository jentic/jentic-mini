package searchclient

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/jentic/jentic-one/cli/internal/httpx"
)

func TestSearchSuccess(t *testing.T) {
	var gotMethod, gotPath, gotAuth string
	var gotBody SearchRequest

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		data, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(data, &gotBody)
		_, _ = w.Write([]byte(`{
			"data": [{
				"type": "operation",
				"api": {"vendor":"acme","name":"users","version":"v1","host":"api.acme.com"},
				"operation_id": "op_abc123",
				"method": "GET",
				"url": "/users",
				"name": "List Users",
				"description": "List all users",
				"relevance_score": 0.95,
				"_links": {"inspect": "/inspect?id=GET%20/users"}
			}],
			"has_more": true,
			"next_cursor": "cursor2"
		}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	result, err := c.Search(context.Background(), "tok123", SearchRequest{
		Query: "list users",
		APIs:  []string{"acme/users/v1"},
		Limit: 5,
	})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if gotMethod != http.MethodPost {
		t.Errorf("method = %q, want POST", gotMethod)
	}
	if gotPath != "/search" {
		t.Errorf("path = %q, want /search", gotPath)
	}
	if gotAuth != "Bearer tok123" {
		t.Errorf("auth = %q", gotAuth)
	}
	if gotBody.Query != "list users" {
		t.Errorf("body.query = %q", gotBody.Query)
	}
	if len(result.Data) != 1 {
		t.Fatalf("got %d results, want 1", len(result.Data))
	}
	hit := result.Data[0]
	if hit.OperationID != "op_abc123" || hit.Score != 0.95 {
		t.Errorf("hit = %+v", hit)
	}
	if hit.URL != "/users" || hit.Method != http.MethodGet {
		t.Errorf("hit method/url = %q %q", hit.Method, hit.URL)
	}
	if hit.API.String() != "acme/users/v1" || hit.API.Host != "api.acme.com" {
		t.Errorf("hit.API = %+v", hit.API)
	}
	if hit.Links.Inspect != "/inspect?id=GET%20/users" {
		t.Errorf("hit.Links.Inspect = %q", hit.Links.Inspect)
	}
	if !result.HasMore || result.NextCursor != "cursor2" {
		t.Errorf("pagination: has_more=%v cursor=%q", result.HasMore, result.NextCursor)
	}
}

// TestSearchDecodesServerSchema guards against drift between SearchHit and the
// server's OperationResultResponse — the api object (not a string) used to abort
// the entire decode (issue #669).
func TestSearchDecodesServerSchema(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{
			"data": [
				{"type":"operation","api":{"vendor":"googleapis-com","name":"googleapis-com-sheets","version":"v4","host":"sheets.googleapis.com"},"operation_id":"op_deadbeef","method":"GET","url":"/v4/spreadsheets/{spreadsheetId}/values/{range}","name":"Get values","relevance_score":0.81,"_links":{"inspect":"/inspect?id=GET%20https://sheets.googleapis.com/v4/spreadsheets/x/values/y"}}
			],
			"has_more": false,
			"next_cursor": ""
		}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	result, err := c.Search(context.Background(), "tok", SearchRequest{Query: "get values from spreadsheet range"})
	if err != nil {
		t.Fatalf("Search must decode a non-empty page without error, got: %v", err)
	}
	if len(result.Data) != 1 {
		t.Fatalf("got %d results, want 1", len(result.Data))
	}
	if result.Data[0].API.Host != "sheets.googleapis.com" {
		t.Errorf("api.host = %q", result.Data[0].API.Host)
	}
}

func TestSearch501MapsToSentinel(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNotImplemented)
		_, _ = w.Write([]byte(`{"detail":"not supported"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.Search(context.Background(), "tok", SearchRequest{Query: "q"})
	if !errors.Is(err, ErrSearchUnsupported) {
		t.Errorf("err = %v, want ErrSearchUnsupported", err)
	}
}

func TestSearchGenericHTTPError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"detail":"server broke"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.Search(context.Background(), "tok", SearchRequest{Query: "q"})
	if err == nil {
		t.Fatal("expected error")
	}
	var he *httpx.HTTPError
	if !errors.As(err, &he) || he.StatusCode != http.StatusInternalServerError {
		t.Errorf("want 500 HTTPError, got %v", err)
	}
}
