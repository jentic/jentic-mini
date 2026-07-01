package agentkey

import (
	"crypto/ed25519"
	"encoding/base64"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestJWKSShape(t *testing.T) {
	k, err := Generate("kid-1")
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	jwks := k.JWKS()
	if len(jwks.Keys) != 1 {
		t.Fatalf("expected 1 key, got %d", len(jwks.Keys))
	}
	j := jwks.Keys[0]
	if j.Kty != "OKP" || j.Crv != "Ed25519" || j.Alg != "EdDSA" || j.Use != "sig" {
		t.Fatalf("unexpected JWK fields: %+v", j)
	}
	if j.Kid != "kid-1" {
		t.Fatalf("kid = %q, want kid-1", j.Kid)
	}
	raw, err := base64.RawURLEncoding.DecodeString(j.X)
	if err != nil {
		t.Fatalf("decode x: %v", err)
	}
	if len(raw) != ed25519.PublicKeySize {
		t.Fatalf("public key size = %d, want %d", len(raw), ed25519.PublicKeySize)
	}
}

func TestSignAssertionVerifiable(t *testing.T) {
	k, err := Generate("kid-7")
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	const (
		agentID = "agnt_abc"
		aud     = "http://127.0.0.1:8000/oauth/token"
	)
	assertion, err := k.SignAssertion(agentID, aud, 2*time.Minute)
	if err != nil {
		t.Fatalf("SignAssertion: %v", err)
	}

	// Verify with the public key recovered from the JWKS, mirroring the server.
	rawPub, _ := base64.RawURLEncoding.DecodeString(k.JWKS().Keys[0].X)
	pub := ed25519.PublicKey(rawPub)

	tok, err := jwt.Parse(assertion, func(token *jwt.Token) (any, error) {
		if token.Method.Alg() != "EdDSA" {
			t.Fatalf("alg = %s, want EdDSA", token.Method.Alg())
		}
		if kid, _ := token.Header["kid"].(string); kid != "kid-7" {
			t.Fatalf("kid header = %v, want kid-7", token.Header["kid"])
		}
		return pub, nil
	}, jwt.WithValidMethods([]string{"EdDSA"}), jwt.WithAudience(aud))
	if err != nil {
		t.Fatalf("verify: %v", err)
	}
	claims := tok.Claims.(jwt.MapClaims)
	if claims["iss"] != agentID || claims["sub"] != agentID {
		t.Fatalf("iss/sub = %v/%v, want %s", claims["iss"], claims["sub"], agentID)
	}
	if _, ok := claims["jti"]; !ok {
		t.Fatalf("missing jti")
	}
}

func TestLoadOrGeneratePersists(t *testing.T) {
	path := filepath.Join(t.TempDir(), "agent.key")

	k1, created, err := LoadOrGenerate(path, "kid-x")
	if err != nil {
		t.Fatalf("LoadOrGenerate(create): %v", err)
	}
	if !created {
		t.Fatalf("expected created=true on first call")
	}

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Fatalf("key perms = %o, want 600", perm)
	}

	k2, created, err := LoadOrGenerate(path, "kid-x")
	if err != nil {
		t.Fatalf("LoadOrGenerate(load): %v", err)
	}
	if created {
		t.Fatalf("expected created=false on second call")
	}
	if !k1.Priv.Equal(k2.Priv) {
		t.Fatalf("reloaded key differs from generated key")
	}
}
