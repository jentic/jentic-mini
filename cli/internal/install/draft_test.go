package install

import "testing"

func TestNewDraftDefaults(t *testing.T) {
	d := NewDraft()
	if d.RuntimePath != RuntimeDocker {
		t.Errorf("RuntimePath = %q", d.RuntimePath)
	}
	if d.DBBackend != BackendSQLite {
		t.Errorf("DBBackend = %q", d.DBBackend)
	}
	if d.IsPostgres() {
		t.Errorf("IsPostgres should be false by default")
	}
	if !d.IsDocker() {
		t.Errorf("IsDocker should be true by default")
	}
	// Local installs enable the file log sink by default.
	if !d.LogFileEnabled {
		t.Errorf("LogFileEnabled should default to true")
	}
	if d.LogFileName != "app.jsonl" {
		t.Errorf("LogFileName = %q, want app.jsonl", d.LogFileName)
	}
}

func TestBaseURL(t *testing.T) {
	cases := []struct {
		host, port, want string
	}{
		{"127.0.0.1", "8000", "http://127.0.0.1:8000"},
		{"0.0.0.0", "9000", "http://127.0.0.1:9000"}, // 0.0.0.0 reported as loopback
		{"", "", "http://127.0.0.1:8000"},            // empty falls back
		{"example.com", "443", "http://example.com:443"},
	}
	for _, tc := range cases {
		d := &Draft{ServerHost: tc.host, ServerPort: tc.port}
		if got := d.BaseURL(); got != tc.want {
			t.Errorf("BaseURL(%q,%q) = %q, want %q", tc.host, tc.port, got, tc.want)
		}
	}
}

func TestCanonicalBaseURL(t *testing.T) {
	d := &Draft{ServerHost: "127.0.0.1", ServerPort: "8000"}
	if got := d.CanonicalBaseURL(); got != "http://127.0.0.1:8000" {
		t.Errorf("derived CanonicalBaseURL = %q", got)
	}
	d.AuthBaseURL = "https://auth.example.com"
	if got := d.CanonicalBaseURL(); got != "https://auth.example.com" {
		t.Errorf("override CanonicalBaseURL = %q", got)
	}
}
