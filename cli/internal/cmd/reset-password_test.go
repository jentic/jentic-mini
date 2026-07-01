package cmd

import (
	"strings"
	"testing"
)

// With --yes the command is non-interactive, so missing or too-short inputs
// must be rejected up front — before any docker/venv dispatch.
func TestResetPasswordNonInteractiveValidation(t *testing.T) {
	cases := []struct {
		name    string
		opts    *resetPasswordOptions
		wantSub string
	}{
		{
			name:    "missing email",
			opts:    &resetPasswordOptions{yes: true, password: "a-strong-password"},
			wantSub: "email is required",
		},
		{
			name:    "short password",
			opts:    &resetPasswordOptions{yes: true, email: "user@example.com", password: "short"},
			wantSub: "at least",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			app := testApp(t)
			err := app.resetPasswordE(tc.opts)
			if err == nil {
				t.Fatalf("expected validation error, got nil")
			}
			if !strings.Contains(err.Error(), tc.wantSub) {
				t.Errorf("error = %q, want substring %q", err.Error(), tc.wantSub)
			}
		})
	}
}

// A valid request against a tempdir with no install must fail at dispatch
// (no compose file, no venv) rather than at input validation — proving inputs
// passed validation and the command tried to act.
func TestResetPasswordRequiresInstall(t *testing.T) {
	app := testApp(t)
	err := app.resetPasswordE(&resetPasswordOptions{
		yes:      true,
		email:    "user@example.com",
		password: "a-strong-password",
	})
	if err == nil {
		t.Fatalf("expected error when not installed")
	}
	if !strings.Contains(err.Error(), "install") {
		t.Errorf("error = %q, want it to point at `jenticctl install`", err.Error())
	}
}
