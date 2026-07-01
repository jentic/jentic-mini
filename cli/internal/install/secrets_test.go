package install

import (
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"testing"
)

func TestFillSecretsPopulatesUniqueValues(t *testing.T) {
	d := NewDraft()
	if err := d.FillSecrets(); err != nil {
		t.Fatalf("FillSecrets: %v", err)
	}

	secrets := []string{d.EncryptionKey, d.AdminJWTSecret, d.AdminInvitePepper, d.ConnectStateSecret}
	seen := map[string]bool{}
	for _, s := range secrets {
		if s == "" {
			t.Fatalf("secret not populated")
		}
		raw, err := base64.StdEncoding.DecodeString(s)
		if err != nil {
			t.Fatalf("secret %q not base64: %v", s, err)
		}
		if len(raw) != 32 {
			t.Errorf("secret length = %d bytes, want 32", len(raw))
		}
		if seen[s] {
			t.Errorf("secrets should be unique; %q repeated", s)
		}
		seen[s] = true
	}
}

func TestFillSecretsNoSSOKeyWithoutSSO(t *testing.T) {
	d := NewDraft()
	if err := d.FillSecrets(); err != nil {
		t.Fatalf("FillSecrets: %v", err)
	}
	if d.IDSigningKeyPEM != "" {
		t.Errorf("id signing key should be empty when SSO disabled")
	}
}

func TestFillSecretsGeneratesES256ForSSO(t *testing.T) {
	d := NewDraft()
	d.SSOEnabled = true
	if err := d.FillSecrets(); err != nil {
		t.Fatalf("FillSecrets: %v", err)
	}
	if d.IDSigningKID == "" {
		t.Errorf("expected a default id signing kid")
	}
	block, _ := pem.Decode([]byte(d.IDSigningKeyPEM))
	if block == nil {
		t.Fatalf("id signing key is not PEM")
	}
	if _, err := x509.ParsePKCS8PrivateKey(block.Bytes); err != nil {
		t.Fatalf("id signing key not a valid PKCS8 key: %v", err)
	}
}
