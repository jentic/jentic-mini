package install

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestAllFormsUseSharedConstructors guards theme consistency: every interactive
// form/input in the CLI must be built through install.NewForm / install.Input so
// it inherits the one brand theme, radio selectors, prompt glyph, and quit keys.
// Constructing huh.NewForm()/huh.NewInput() directly anywhere else bypasses the
// theme (that is how the register form once showed a default ">" prompt), so we
// fail the build if any such call appears outside this package's theme.go.
func TestAllFormsUseSharedConstructors(t *testing.T) {
	root := moduleRoot(t)

	// The only sanctioned home of the raw huh constructors.
	allowed := filepath.Join(root, "internal", "install", "theme.go")
	forbidden := []string{"huh.NewForm(", "huh.NewInput("}

	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		if path == allowed {
			return nil
		}
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		src := string(data)
		for _, tok := range forbidden {
			if strings.Contains(src, tok) {
				rel, _ := filepath.Rel(root, path)
				t.Errorf("%s calls %s directly; use install.NewForm / install.Input instead", rel, tok)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk module: %v", err)
	}
}

// moduleRoot walks up from the test's working directory to the dir holding go.mod.
func moduleRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	for {
		if _, statErr := os.Stat(filepath.Join(dir, "go.mod")); statErr == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatalf("go.mod not found from %s upward", dir)
		}
		dir = parent
	}
}
