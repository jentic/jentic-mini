package authclient

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/jentic/jentic-one/cli/internal/agentkey"
)

func TestAudienceTrimsSlash(t *testing.T) {
	c := New("http://host:8000/")
	if got := c.Audience(); got != "http://host:8000/oauth/token" {
		t.Fatalf("Audience = %q", got)
	}
}

func TestRegister(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/register" || r.Method != http.MethodPost {
			t.Errorf("unexpected request %s %s", r.Method, r.URL.Path)
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["client_name"] != "agent-x" {
			t.Errorf("client_name = %v", body["client_name"])
		}
		_ = json.NewEncoder(w).Encode(RegistrationResult{
			ClientID: "agnt_1", Status: "pending", RegistrationAccessToken: "rat_1",
		})
	}))
	defer srv.Close()

	k, _ := agentkey.Generate("kid-1")
	got, err := New(srv.URL).Register(context.Background(), "agent-x", k.JWKS())
	if err != nil {
		t.Fatalf("Register: %v", err)
	}
	if got.ClientID != "agnt_1" || got.Status != "pending" || got.RegistrationAccessToken != "rat_1" {
		t.Fatalf("unexpected result: %+v", got)
	}
}

func TestMintAgentTokenSuccess(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/oauth/token" {
			t.Errorf("path = %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(TokenPair{AccessToken: "at", RefreshToken: "rt", ExpiresIn: 3600})
	}))
	defer srv.Close()

	pair, err := New(srv.URL).MintAgentToken(context.Background(), "assertion")
	if err != nil {
		t.Fatalf("MintAgentToken: %v", err)
	}
	if pair.AccessToken != "at" || pair.ExpiresIn != 3600 {
		t.Fatalf("unexpected pair: %+v", pair)
	}
}

func TestMintAgentTokenPending(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error":             "invalid_grant",
			"error_description": "agent not active",
		})
	}))
	defer srv.Close()

	_, err := New(srv.URL).MintAgentToken(context.Background(), "assertion")
	var pending *PendingError
	if !errors.As(err, &pending) {
		t.Fatalf("expected *PendingError, got %v", err)
	}
	if pending.Error() != "agent not active" {
		t.Fatalf("PendingError detail = %q", pending.Error())
	}
}

func TestRefresh(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["grant_type"] != "refresh_token" || body["refresh_token"] != "rt-old" {
			t.Errorf("unexpected body %+v", body)
		}
		_ = json.NewEncoder(w).Encode(TokenPair{AccessToken: "at-new", RefreshToken: "rt-new"})
	}))
	defer srv.Close()

	pair, err := New(srv.URL).Refresh(context.Background(), "rt-old")
	if err != nil {
		t.Fatalf("Refresh: %v", err)
	}
	if pair.AccessToken != "at-new" {
		t.Fatalf("AccessToken = %q", pair.AccessToken)
	}
}

func TestMe(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("Authorization"); got != "Bearer at-1" {
			t.Errorf("Authorization = %q", got)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"sub": "agnt_1"})
	}))
	defer srv.Close()

	me, err := New(srv.URL).Me(context.Background(), "at-1")
	if err != nil {
		t.Fatalf("Me: %v", err)
	}
	if me["sub"] != "agnt_1" {
		t.Fatalf("me = %+v", me)
	}
}

func TestRevokeTransportError(t *testing.T) {
	// Closed server -> transport error surfaces.
	srv := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	url := srv.URL
	srv.Close()
	if err := New(url).Revoke(context.Background(), "at", "rt"); err == nil {
		t.Fatalf("expected transport error from closed server")
	}
}

func TestHTTPErrorDetail(t *testing.T) {
	cases := []struct {
		body string
		want string
	}{
		{`{"detail":"boom"}`, "boom"},
		{`{"error_description":"bad grant"}`, "bad grant"},
		{`{"error":"invalid"}`, "invalid"},
		{`not json`, "not json"},
	}
	for _, tc := range cases {
		e := &HTTPError{StatusCode: 400, Body: tc.body}
		if got := e.Detail(); got != tc.want {
			t.Errorf("Detail(%q) = %q, want %q", tc.body, got, tc.want)
		}
	}
}
