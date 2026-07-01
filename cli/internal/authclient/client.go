// Package authclient is a thin HTTP client for the Jentic auth surface: agent
// Dynamic Client Registration, JWT-Bearer token minting, refresh, identity, and
// revocation.
package authclient

import (
	"context"
	"errors"
	"net/http"
	"time"

	"github.com/jentic/jentic-one/cli/internal/agentkey"
	"github.com/jentic/jentic-one/cli/internal/httpx"
)

// PendingError indicates the agent is not yet active (token exchange returned a
// retryable invalid_grant). Callers should wait for approval and retry.
type PendingError struct {
	Detail string
}

func (e *PendingError) Error() string {
	if e.Detail == "" {
		return "agent not active yet (pending approval)"
	}
	return e.Detail
}

// Client talks to a single Jentic control-plane base URL.
type Client struct {
	http *httpx.Client
}

// New returns a client for the given base URL (trailing slash trimmed).
//
// The timeout is generous (60s) because token minting writes to the admin DB,
// which under the SQLite backend can briefly queue behind another writer (a
// concurrent broker execution or job) holding the single file-wide write lock.
// The mint waits out that lock via busy_timeout + retry, so a short client
// timeout would surface a spurious "context deadline exceeded" for a request
// that is about to succeed.
func New(baseURL string) *Client {
	return &Client{http: httpx.New(baseURL, 60*time.Second)}
}

// HTTPError is the shared problem-details transport error.
type HTTPError = httpx.HTTPError

// Audience is the expected JWT-Bearer assertion audience for this base URL.
func (c *Client) Audience() string { return c.http.BaseURL() + "/oauth/token" }

// RegistrationResult is the response from Dynamic Client Registration.
type RegistrationResult struct {
	ClientID                string `json:"client_id"`
	Status                  string `json:"status"`
	RegistrationAccessToken string `json:"registration_access_token"`
}

// Register performs RFC 7591 Dynamic Client Registration for an agent.
func (c *Client) Register(ctx context.Context, clientName string, jwks agentkey.JWKS) (*RegistrationResult, error) {
	body := map[string]any{"client_name": clientName, "jwks": jwks}
	var out RegistrationResult
	if err := c.http.Do(ctx, http.MethodPost, "/register", "", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TokenPair is an opaque access/refresh token pair.
type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
}

// MintAgentToken exchanges a signed JWT-Bearer assertion for a token pair.
// A retryable invalid_grant (HTTP 400) is reported as *PendingError.
func (c *Client) MintAgentToken(ctx context.Context, assertion string) (*TokenPair, error) {
	body := map[string]string{
		"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
		"assertion":  assertion,
	}
	var out TokenPair
	if err := c.http.Do(ctx, http.MethodPost, "/oauth/token", "", body, &out); err != nil {
		var he *HTTPError
		if errors.As(err, &he) && he.StatusCode == http.StatusBadRequest {
			return nil, &PendingError{Detail: he.Detail()}
		}
		return nil, err
	}
	return &out, nil
}

// Refresh rotates a token pair using the refresh_token grant.
func (c *Client) Refresh(ctx context.Context, refreshToken string) (*TokenPair, error) {
	body := map[string]string{"grant_type": "refresh_token", "refresh_token": refreshToken}
	var out TokenPair
	if err := c.http.Do(ctx, http.MethodPost, "/oauth/token", "", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Me returns the caller identity for the given access token.
func (c *Client) Me(ctx context.Context, accessToken string) (map[string]any, error) {
	var out map[string]any
	if err := c.http.Do(ctx, http.MethodGet, "/me", accessToken, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// Revoke revokes a token (RFC 7009). Best-effort; always treated as success by
// the server, but transport errors are returned.
func (c *Client) Revoke(ctx context.Context, accessToken, token string) error {
	body := map[string]string{"token": token}
	return c.http.Do(ctx, http.MethodPost, "/oauth/revoke", accessToken, body, nil)
}
