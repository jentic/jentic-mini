package accessclient

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/jentic/jentic-one/cli/internal/httpx"
)

func TestFileSendsItemsAndDecodes(t *testing.T) {
	var gotAuth, gotPath, gotMethod string
	var gotBody FileRequest
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		gotPath = r.URL.Path
		gotMethod = r.Method
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &gotBody)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{
			"id":"arq_1","actor_id":"agnt_1","status":"pending",
			"approve_url":"https://cp/access-requests/arq_1",
			"filed_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-08T00:00:00Z",
			"items":[{"id":"arqi_1","resource_type":"toolkit","action":"bind","status":"pending"}]}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	req := FileRequest{
		Reason: "need httpbin",
		Items: []Item{{
			ResourceType:      "toolkit",
			Action:            "bind",
			ResourceReference: map[string]any{"vendor": "httpbin.org", "name": "httpbin"},
		}},
	}
	out, err := c.File(context.Background(), "tok", req)
	if err != nil {
		t.Fatalf("File: %v", err)
	}
	if gotAuth != "Bearer tok" {
		t.Errorf("auth = %q", gotAuth)
	}
	if gotMethod != http.MethodPost || gotPath != "/access-requests" {
		t.Errorf("%s %s, want POST /access-requests", gotMethod, gotPath)
	}
	if len(gotBody.Items) != 1 || gotBody.Items[0].ResourceReference["vendor"] != "httpbin.org" {
		t.Errorf("request body not sent faithfully: %+v", gotBody)
	}
	if out.ID != "arq_1" || out.Status != StatusPending || out.ApproveURL == "" {
		t.Errorf("decoded = %+v", out)
	}
	if out.IsTerminal() {
		t.Error("pending request should not be terminal")
	}
}

func TestFileOmitsEmptyOptionalItemFields(t *testing.T) {
	var raw map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &raw)
		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{"id":"arq_1","actor_id":"a","status":"pending","approve_url":"u",
			"filed_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-08T00:00:00Z","items":[]}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.File(context.Background(), "tok", FileRequest{
		Items: []Item{{ResourceType: "scope", Action: "grant", ResourceID: "apis:read"}},
	})
	if err != nil {
		t.Fatalf("File: %v", err)
	}
	item := raw["items"].([]any)[0].(map[string]any)
	for _, k := range []string{"resource_reference", "to_id", "to_type", "rules"} {
		if _, present := item[k]; present {
			t.Errorf("empty optional %q should be omitted, got item=%v", k, item)
		}
	}
	if _, present := raw["reason"]; present {
		t.Error("empty reason should be omitted")
	}
}

func TestFileDuplicatePendingMapsToTypedError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/problem+json")
		w.WriteHeader(http.StatusConflict)
		_, _ = w.Write([]byte(`{"type":"access_request_duplicate_pending","title":"dup",
			"status":409,"existing_request_id":"arq_existing",
			"approve_url":"https://cp/access-requests/arq_existing"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.File(context.Background(), "tok", FileRequest{
		Items: []Item{{ResourceType: "toolkit", Action: "bind", ResourceID: "tk_1"}},
	})
	if !errors.Is(err, ErrDuplicatePending) {
		t.Fatalf("err = %v, want ErrDuplicatePending", err)
	}
	var dup *DuplicatePendingError
	if !errors.As(err, &dup) {
		t.Fatalf("err = %v, want *DuplicatePendingError", err)
	}
	if dup.ExistingRequestID != "arq_existing" || dup.ApproveURL == "" {
		t.Errorf("dup = %+v", dup)
	}
}

func TestListSendsFiltersAndDecodesPage(t *testing.T) {
	var gotQuery string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotQuery = r.URL.RawQuery
		_, _ = w.Write([]byte(`{"data":[
			{"id":"arq_1","actor_id":"a","status":"pending","approve_url":"u",
			 "filed_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-08T00:00:00Z","items":[]}],
			"has_more":true,"next_cursor":"c2"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	res, err := c.List(context.Background(), "tok", StatusPending, "c1", 25)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	for _, want := range []string{"status=pending", "cursor=c1", "limit=25"} {
		if !strings.Contains(gotQuery, want) {
			t.Errorf("query %q missing %q", gotQuery, want)
		}
	}
	if len(res.Data) != 1 || !res.HasMore || res.NextCursor != "c2" {
		t.Errorf("page = %+v", res)
	}
}

func TestGetWithdrawAmendPaths(t *testing.T) {
	var paths []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.Method+" "+r.URL.Path)
		_, _ = w.Write([]byte(`{"id":"arq_1","actor_id":"a","status":"withdrawn","approve_url":"u",
			"filed_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-08T00:00:00Z","items":[]}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	if _, err := c.Get(context.Background(), "tok", "arq_1"); err != nil {
		t.Fatalf("Get: %v", err)
	}
	if _, err := c.Withdraw(context.Background(), "tok", "arq_1"); err != nil {
		t.Fatalf("Withdraw: %v", err)
	}
	if _, err := c.Amend(context.Background(), "tok", "arq_1", []AmendItem{{ItemID: "arqi_1", ResourceID: "tk_2"}}); err != nil {
		t.Fatalf("Amend: %v", err)
	}
	want := []string{
		"GET /access-requests/arq_1",
		"POST /access-requests/arq_1:withdraw",
		"POST /access-requests/arq_1:amend",
	}
	for i, w := range want {
		if i >= len(paths) || paths[i] != w {
			t.Errorf("call %d = %q, want %q", i, paths[i], w)
		}
	}
}

func TestMeDecodesBindings(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/me" {
			t.Errorf("path = %q, want /me", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"id":"agnt_1","name":"demo","status":"active",
			"scopes":["capabilities:execute","owner:access-requests:read"],
			"token_scopes":["capabilities:execute"],
			"toolkit_bindings":[{"toolkit_id":"tk_1","bound_at":"2026-01-01T00:00:00Z"}]}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	me, err := c.Me(context.Background(), "tok")
	if err != nil {
		t.Fatalf("Me: %v", err)
	}
	if me.ID != "agnt_1" || len(me.Scopes) != 2 || len(me.ToolkitBindings) != 1 {
		t.Errorf("me = %+v", me)
	}
	if me.ToolkitBindings[0].ToolkitID != "tk_1" {
		t.Errorf("binding = %+v", me.ToolkitBindings[0])
	}
}

func TestStaleScopes(t *testing.T) {
	cases := []struct {
		name        string
		scopes      []string
		tokenScopes []string
		want        []string
	}{
		{
			name:        "grant landed after token mint surfaces as stale",
			scopes:      []string{"capabilities:execute", "owner:access-requests:read"},
			tokenScopes: []string{"capabilities:execute"},
			want:        []string{"owner:access-requests:read"},
		},
		{
			name:        "token already carries every grant",
			scopes:      []string{"capabilities:execute"},
			tokenScopes: []string{"capabilities:execute"},
			want:        nil,
		},
		{
			name:        "token may carry scopes no longer granted; those are not stale",
			scopes:      []string{"capabilities:execute"},
			tokenScopes: []string{"capabilities:execute", "stale:revoked"},
			want:        nil,
		},
		{
			name:        "absent token_scopes (old server) is unknown, not all-stale",
			scopes:      []string{"a", "b"},
			tokenScopes: nil,
			want:        nil,
		},
		{
			name:        "explicitly empty token_scopes means every grant is stale",
			scopes:      []string{"a", "b"},
			tokenScopes: []string{},
			want:        []string{"a", "b"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			m := &Me{Scopes: tc.scopes, TokenScopes: tc.tokenScopes}
			got := m.StaleScopes()
			if strings.Join(got, ",") != strings.Join(tc.want, ",") {
				t.Errorf("StaleScopes() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestMeRejectsNonAgentToken(t *testing.T) {
	// GET /me returns a discriminated union; a user/service-account token must be
	// rejected rather than silently decoded into an agent-shaped Me with no
	// bindings (which would misread as "approved agent, no toolkits").
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"type":"user","id":"usr_1","name":"admin","status":"active",
			"scopes":["org:admin"]}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.Me(context.Background(), "tok")
	if err == nil {
		t.Fatal("expected error for non-agent token, got nil")
	}
	if !strings.Contains(err.Error(), "user") || !strings.Contains(err.Error(), "agent token") {
		t.Errorf("error = %q, want it to name the actor type and require an agent token", err.Error())
	}
}

func TestGenericHTTPErrorPropagates(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
		_, _ = w.Write([]byte(`{"detail":"down"}`))
	}))
	defer srv.Close()

	c := New(srv.URL)
	_, err := c.List(context.Background(), "tok", "", "", 0)
	var he *httpx.HTTPError
	if !errors.As(err, &he) || he.StatusCode != http.StatusServiceUnavailable {
		t.Fatalf("err = %v, want 503 HTTPError", err)
	}
}
