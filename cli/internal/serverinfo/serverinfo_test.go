package serverinfo

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestProbeReportsVersionWhenHealthy(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			http.NotFound(w, r)
			return
		}
		_, _ = w.Write([]byte(`{"status":"ok","surface":"control","version":"9.9.9"}`))
	}))
	defer srv.Close()

	got := Probe(srv.URL, DefaultTimeout)
	if !got.Running {
		t.Fatalf("Probe.Running = false, want true")
	}
	if got.Version != "9.9.9" {
		t.Errorf("Probe.Version = %q, want 9.9.9", got.Version)
	}
}

func TestProbeRunningWithoutVersion(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"status":"ok","surface":"control"}`))
	}))
	defer srv.Close()

	got := Probe(srv.URL, DefaultTimeout)
	if !got.Running || got.Version != "" {
		t.Errorf("Probe = %+v, want running with empty version", got)
	}
}

func TestProbeNotRunningOn500(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	if got := Probe(srv.URL, DefaultTimeout); got.Running {
		t.Errorf("Probe.Running = true on 500, want false")
	}
}

func TestProbeNotRunningWhenUnreachable(t *testing.T) {
	// Closed server: connection refused should yield Running=false quickly.
	srv := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	url := srv.URL
	srv.Close()

	if got := Probe(url, 200*time.Millisecond); got.Running {
		t.Errorf("Probe.Running = true for closed server, want false")
	}
}

func TestProbeEmptyBaseURL(t *testing.T) {
	if got := Probe("", DefaultTimeout); got.Running {
		t.Errorf("Probe.Running = true for empty base URL, want false")
	}
}
