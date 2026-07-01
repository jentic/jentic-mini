// Package agentauth ties together a profile, its Ed25519 key, and the auth
// client to register agents and resolve valid access tokens (mint/refresh).
package agentauth

import (
	"context"
	"errors"
	"time"

	"github.com/jentic/jentic-one/cli/internal/agentkey"
	"github.com/jentic/jentic-one/cli/internal/authclient"
	"github.com/jentic/jentic-one/cli/internal/config"
	"github.com/jentic/jentic-one/cli/internal/profile"
)

// expirySkew re-mints a token slightly before it actually expires.
const expirySkew = 60 * time.Second

// assertionTTL is the lifetime of a signed JWT-Bearer assertion.
const assertionTTL = 2 * time.Minute

// Session bundles a profile + key + client for a single base URL.
type Session struct {
	Profile *profile.Profile
	Meta    *profile.Meta
	Key     *agentkey.Key
	Client  *authclient.Client
	// APIKey holds the stored API key when Meta.AuthMode is AuthModeAPIKey.
	APIKey string
}

// ErrNotRegistered is returned when the profile has no agent id yet.
var ErrNotRegistered = errors.New("profile has no registered agent; run `jentic register` first")

// ErrNoAPIKey is returned when an API-key profile has no key stored.
var ErrNoAPIKey = errors.New("profile has no API key; run `jentic profile add-key` first")

// Open loads the profile metadata and key for a base URL, generating the key if
// missing. It does not perform registration. For API-key profiles it loads the
// stored key instead of generating an Ed25519 keypair.
func Open(paths config.Paths, profileName, baseURL string) (*Session, error) {
	p, err := profile.Open(paths, profileName)
	if err != nil {
		return nil, err
	}
	meta, err := p.LoadMeta()
	if err != nil {
		return nil, err
	}
	if meta.BaseURL == "" {
		meta.BaseURL = baseURL
	}

	sess := &Session{
		Profile: p,
		Meta:    meta,
		Client:  authclient.New(meta.BaseURL),
	}

	if meta.IsAPIKey() {
		apiKey, keyErr := p.LoadAPIKey()
		if keyErr != nil {
			return nil, keyErr
		}
		sess.APIKey = apiKey
		return sess, nil
	}

	if meta.KID == "" {
		meta.KID = "jentic-cli-" + p.Name
	}
	key, _, err := agentkey.LoadOrGenerate(p.KeyPath(), meta.KID)
	if err != nil {
		return nil, err
	}
	sess.Key = key
	return sess, nil
}

// ResetRegistration clears all DCR registration state from the session's
// profile metadata so a subsequent register call provisions a brand-new agent.
// It clears the agent id, the human-friendly name, and the RFC 7592 management
// token together — clearing only the id would leave stale name/token fields.
func (s *Session) ResetRegistration() {
	s.Meta.AgentID = ""
	s.Meta.AgentName = ""
	s.Meta.RegistrationAccessToken = ""
}

// MintFresh signs an assertion and exchanges it for a new token pair, saving it
// to the profile. Returns *authclient.PendingError while the agent is not active.
func (s *Session) MintFresh(ctx context.Context) (*profile.Tokens, error) {
	if s.Meta.AgentID == "" {
		return nil, ErrNotRegistered
	}
	assertion, err := s.Key.SignAssertion(s.Meta.AgentID, s.Client.Audience(), assertionTTL)
	if err != nil {
		return nil, err
	}
	pair, err := s.Client.MintAgentToken(ctx, assertion)
	if err != nil {
		return nil, err
	}
	return s.persist(pair)
}

// ValidToken returns a non-expired access token, refreshing or re-minting as
// needed, and persists any new pair. For API-key profiles it returns the stored
// API key directly (it is the bearer credential — no minting or caching).
func (s *Session) ValidToken(ctx context.Context) (string, error) {
	if s.Meta.IsAPIKey() {
		if s.APIKey == "" {
			return "", ErrNoAPIKey
		}
		return s.APIKey, nil
	}
	if s.Meta.AgentID == "" {
		return "", ErrNotRegistered
	}
	// LoadTokens returns (nil, nil) when no token file exists yet; Expired
	// treats a nil receiver as expired, so an absent cache short-circuits
	// straight to the mint path below. The explicit nil guard before the refresh
	// branch is the safety net that keeps that case from dereferencing nil.
	tokens, err := s.Profile.LoadTokens()
	if err != nil {
		return "", err
	}
	if !tokens.Expired(expirySkew) {
		return tokens.AccessToken, nil
	}

	// Try refresh first when we have a refresh token.
	if tokens != nil && tokens.RefreshToken != "" {
		if pair, refErr := s.Client.Refresh(ctx, tokens.RefreshToken); refErr == nil {
			saved, saveErr := s.persist(pair)
			if saveErr != nil {
				return "", saveErr
			}
			return saved.AccessToken, nil
		}
	}

	// Fall back to minting a fresh pair from a new assertion.
	saved, mintErr := s.MintFresh(ctx)
	if mintErr != nil {
		return "", mintErr
	}
	return saved.AccessToken, nil
}

func (s *Session) persist(pair *authclient.TokenPair) (*profile.Tokens, error) {
	expiresAt := time.Time{}
	if pair.ExpiresIn > 0 {
		expiresAt = time.Now().Add(time.Duration(pair.ExpiresIn) * time.Second)
	}
	tokens := &profile.Tokens{
		AccessToken:     pair.AccessToken,
		RefreshToken:    pair.RefreshToken,
		AccessExpiresAt: expiresAt,
	}
	if err := s.Profile.SaveTokens(tokens); err != nil {
		return nil, err
	}
	return tokens, nil
}
