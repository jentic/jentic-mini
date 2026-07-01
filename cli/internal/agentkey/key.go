// Package agentkey handles the agent's Ed25519 identity key: generation,
// PEM persistence, JWKS publication, and JWT-Bearer assertion signing.
package agentkey

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// JWK is a single JSON Web Key for an Ed25519 public key (OKP).
type JWK struct {
	Kty string `json:"kty"`
	Crv string `json:"crv"`
	X   string `json:"x"`
	Kid string `json:"kid"`
	Use string `json:"use"`
	Alg string `json:"alg"`
}

// JWKS is a JSON Web Key Set.
type JWKS struct {
	Keys []JWK `json:"keys"`
}

// Key wraps an Ed25519 private key plus its key id.
type Key struct {
	Priv ed25519.PrivateKey
	KID  string
}

// Generate creates a new Ed25519 key with the given key id.
func Generate(kid string) (*Key, error) {
	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, err
	}
	return &Key{Priv: priv, KID: kid}, nil
}

// LoadOrGenerate loads the key from path, or generates and persists a new one
// (PEM, 0600) using kid when the file does not exist. It reports whether a new
// key was created.
func LoadOrGenerate(path, kid string) (key *Key, created bool, err error) {
	data, readErr := os.ReadFile(path) //nolint:gosec // path is a CLI-managed key file under JENTIC_HOME, not user input.
	if readErr == nil {
		k, loadErr := parsePEM(data, kid)
		return k, false, loadErr
	}
	if !errors.Is(readErr, fs.ErrNotExist) {
		return nil, false, readErr
	}

	k, genErr := Generate(kid)
	if genErr != nil {
		return nil, false, genErr
	}
	if saveErr := k.Save(path); saveErr != nil {
		return nil, false, saveErr
	}
	return k, true, nil
}

// Save writes the private key as PKCS#8 PEM with 0600 perms.
func (k *Key) Save(path string) error {
	der, err := x509.MarshalPKCS8PrivateKey(k.Priv)
	if err != nil {
		return err
	}
	block := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der})
	return os.WriteFile(path, block, 0o600)
}

func parsePEM(data []byte, kid string) (*Key, error) {
	block, _ := pem.Decode(data)
	if block == nil {
		return nil, errors.New("invalid PEM in agent key file")
	}
	parsed, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("parse agent key: %w", err)
	}
	priv, ok := parsed.(ed25519.PrivateKey)
	if !ok {
		return nil, errors.New("agent key is not Ed25519")
	}
	return &Key{Priv: priv, KID: kid}, nil
}

// JWKS returns the public JWKS for this key.
func (k *Key) JWKS() JWKS {
	pub := k.Priv.Public().(ed25519.PublicKey)
	return JWKS{Keys: []JWK{{
		Kty: "OKP",
		Crv: "Ed25519",
		X:   base64.RawURLEncoding.EncodeToString(pub),
		Kid: k.KID,
		Use: "sig",
		Alg: "EdDSA",
	}}}
}

// SignAssertion produces a short-lived JWT-Bearer assertion (alg=EdDSA) for the
// given agent id and audience, as expected by the token endpoint.
func (k *Key) SignAssertion(agentID, audience string, ttl time.Duration) (string, error) {
	now := time.Now()
	claims := jwt.MapClaims{
		"iss": agentID,
		"sub": agentID,
		"aud": audience,
		"iat": now.Unix(),
		"exp": now.Add(ttl).Unix(),
		"jti": uuid.NewString(),
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tok.Header["kid"] = k.KID
	return tok.SignedString(k.Priv)
}
