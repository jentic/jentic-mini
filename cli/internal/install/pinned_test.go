package install

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPinnedBannerInertOnNonTTY(t *testing.T) {
	// A regular file is not a TTY, so the banner controller must be inert and
	// must not write escape sequences or the banner into the stream.
	path := filepath.Join(t.TempDir(), "out.txt")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	defer f.Close()

	banner := StartPinnedBanner(f)
	banner.Stop() // must be a no-op, no panic

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if info.Size() != 0 {
		t.Errorf("inert banner wrote %d bytes, want 0", info.Size())
	}
}
