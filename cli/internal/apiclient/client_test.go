package apiclient

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestListSendsVendorAndDecodes(t *testing.T) {
	var gotPath, gotVendor, gotAuth string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotVendor = r.URL.Query().Get("vendor")
		gotAuth = r.Header.Get("Authorization")
		_, _ = w.Write([]byte(`{"data":[{"api":{"vendor":"stripe.com","name":"api","version":"v1"},
			"operation_count":3,"revision_count":1,"security_schemes":["bearer"]}],
			"has_more":false,"next_cursor":""}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	out, err := c.List(context.Background(), "tok", ListParams{Vendor: "stripe.com", Limit: 50})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if gotPath != "/apis" {
		t.Errorf("path = %q, want /apis", gotPath)
	}
	if gotVendor != "stripe.com" {
		t.Errorf("vendor = %q", gotVendor)
	}
	if gotAuth != "Bearer tok" {
		t.Errorf("auth = %q", gotAuth)
	}
	if len(out.Data) != 1 || out.Data[0].API.Vendor != "stripe.com" || out.Data[0].OperationCount != 3 {
		t.Errorf("decoded unexpectedly: %+v", out.Data)
	}
}

func TestGetEscapesSegments(t *testing.T) {
	var gotPath string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.EscapedPath()
		_, _ = w.Write([]byte(`{"api":{"vendor":"acme corp","name":"n","version":"v1"}}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	if _, err := c.Get(context.Background(), "tok", "acme corp", "n", "v1"); err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !strings.Contains(gotPath, "acme%20corp") {
		t.Errorf("vendor segment not escaped: %q", gotPath)
	}
}

func TestRevisionsRepeatsStateParam(t *testing.T) {
	var states []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		states = r.URL.Query()["state"]
		_, _ = w.Write([]byte(`{"data":[],"has_more":false}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.Revisions(context.Background(), "tok", "v", "n", "1", RevisionParams{States: []string{"draft", "archived"}})
	if err != nil {
		t.Fatalf("Revisions: %v", err)
	}
	if len(states) != 2 || states[0] != "draft" || states[1] != "archived" {
		t.Errorf("state params = %v, want [draft archived]", states)
	}
}

func TestOperationsLiveVsRevision(t *testing.T) {
	var paths []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		_, _ = w.Write([]byte(`{"data":[],"has_more":false}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	if _, err := c.Operations(context.Background(), "tok", "v", "n", "1", "", "", 0); err != nil {
		t.Fatalf("live ops: %v", err)
	}
	if _, err := c.Operations(context.Background(), "tok", "v", "n", "1", "rev9", "", 0); err != nil {
		t.Fatalf("rev ops: %v", err)
	}
	if !strings.HasSuffix(paths[0], "/v/n/1/operations") {
		t.Errorf("live ops path = %q", paths[0])
	}
	if !strings.Contains(paths[1], "/revisions/rev9/operations") {
		t.Errorf("rev ops path = %q", paths[1])
	}
}

func TestPromoteArchiveDeletePaths(t *testing.T) {
	var method, path string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		method, path = r.Method, r.URL.Path
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	c := New(srv.URL)
	if err := c.Promote(context.Background(), "tok", "v", "n", "1", "r1"); err != nil {
		t.Fatalf("Promote: %v", err)
	}
	if method != http.MethodPost || !strings.HasSuffix(path, "/revisions/r1:promote") {
		t.Errorf("promote = %s %s", method, path)
	}
	if err := c.Archive(context.Background(), "tok", "v", "n", "1", "r1"); err != nil {
		t.Fatalf("Archive: %v", err)
	}
	if !strings.HasSuffix(path, "/revisions/r1:archive") {
		t.Errorf("archive path = %s", path)
	}
	if err := c.DeleteAPI(context.Background(), "tok", "v", "n", "1"); err != nil {
		t.Fatalf("DeleteAPI: %v", err)
	}
	if method != http.MethodDelete || !strings.HasSuffix(path, "/apis/v/n/1") {
		t.Errorf("delete api = %s %s", method, path)
	}
}

func TestSpecAndInspectAcceptHeaders(t *testing.T) {
	var accept string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		accept = r.Header.Get("Accept")
		_, _ = w.Write([]byte("raw-body"))
	}))
	defer srv.Close()

	c := New(srv.URL)
	body, err := c.Spec(context.Background(), "tok", "v", "n", "1", "", true)
	if err != nil {
		t.Fatalf("Spec: %v", err)
	}
	if accept != "application/yaml" {
		t.Errorf("spec accept = %q", accept)
	}
	if string(body) != "raw-body" {
		t.Errorf("spec body = %q", body)
	}
	if _, err := c.Inspect(context.Background(), "tok", "op1", "", "markdown"); err != nil {
		t.Fatalf("Inspect: %v", err)
	}
	if accept != "text/markdown" {
		t.Errorf("inspect accept = %q", accept)
	}
}

func TestInspectRoutesMethodURLToIDParam(t *testing.T) {
	var gotQuery url.Values
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotQuery = r.URL.Query()
		_, _ = w.Write([]byte("ok"))
	}))
	defer srv.Close()

	c := New(srv.URL)

	if _, err := c.Inspect(context.Background(), "tok", "GET https://rest.coincap.io/v3/markets", "", "json"); err != nil {
		t.Fatalf("Inspect: %v", err)
	}
	if got := gotQuery.Get("id"); got != "GET https://rest.coincap.io/v3/markets" {
		t.Errorf("id = %q, want METHOD URL", got)
	}
	if gotQuery.Has("operation_id") {
		t.Errorf("operation_id should not be set for METHOD URL form: %v", gotQuery)
	}

	if _, err := c.Inspect(context.Background(), "tok", "listPets", "", "json"); err != nil {
		t.Fatalf("Inspect: %v", err)
	}
	if got := gotQuery.Get("operation_id"); got != "listPets" {
		t.Errorf("operation_id = %q, want opaque id", got)
	}
	if gotQuery.Has("id") {
		t.Errorf("id should not be set for opaque operation_id: %v", gotQuery)
	}
}

func TestHTTPErrorDetail(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"detail":"API not found"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.Get(context.Background(), "tok", "v", "n", "1")
	var he *HTTPError
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "API not found") {
		t.Errorf("error = %v", err)
	}
	errors.As(err, &he)
	if he == nil || he.StatusCode != http.StatusNotFound {
		t.Errorf("want 404 HTTPError, got %v", err)
	}
}
