// Package serverinfo probes a running jentic-one server for liveness and
// version, used to decorate the help screen and install wizard with the
// server's version alongside the CLI's own.
package serverinfo

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"
)

// DefaultTimeout bounds the health probe so interactive surfaces (help screen,
// install wizard) never block noticeably when the server is down or slow.
const DefaultTimeout = 400 * time.Millisecond

// Info is the result of probing the server's health endpoint.
type Info struct {
	// Running reports whether GET {baseURL}/health returned 200.
	Running bool
	// Version is the server's reported version (empty if the server is down or
	// does not report one).
	Version string
}

// healthResponse mirrors the fields we care about from GET /health. The server
// reports its version here (in addition to status/surface).
type healthResponse struct {
	Status  string `json:"status"`
	Version string `json:"version"`
}

// Probe queries {baseURL}/health and reports whether the server is reachable
// and its version. It is best-effort: any error (down, timeout, bad payload)
// yields a zero Info with Running=false.
func Probe(baseURL string, timeout time.Duration) Info {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		return Info{}
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, base+"/health", nil)
	if err != nil {
		return Info{}
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return Info{}
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != http.StatusOK {
		return Info{}
	}

	var body healthResponse
	// Cap the read so a misbehaving endpoint can't stream unbounded data.
	_ = json.NewDecoder(io.LimitReader(resp.Body, 1<<16)).Decode(&body)
	return Info{Running: true, Version: body.Version}
}
