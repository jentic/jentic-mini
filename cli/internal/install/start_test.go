package install

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestTailFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "log.txt")
	if err := os.WriteFile(path, []byte("l1\nl2\nl3\nl4\nl5\n"), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
	got := tailFile(path, 2)
	if !strings.Contains(got, "l4") || !strings.Contains(got, "l5") {
		t.Errorf("tail should contain last lines, got %q", got)
	}
	if strings.Contains(got, "l1") {
		t.Errorf("tail should drop earlier lines, got %q", got)
	}
}

func TestTailFileMissing(t *testing.T) {
	if got := tailFile(filepath.Join(t.TempDir(), "nope"), 5); got != "" {
		t.Errorf("missing file tail = %q, want empty", got)
	}
}

func TestStartAppDetectsEarlyCrash(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell-script fixture is POSIX-only")
	}

	// Widen the early-exit window so a fixture that crashes immediately is
	// detected deterministically: StartApp returns as soon as cmd.Wait() sees
	// the exit, and a generous window means the timer can never win the race
	// even when the parallel test suite starves the scheduler. Restored after.
	prev := earlyExitWindow
	earlyExitWindow = 30 * time.Second
	t.Cleanup(func() { earlyExitWindow = prev })

	dir := t.TempDir()

	// A fake interpreter that crashes immediately, ignoring its args.
	fakePy := filepath.Join(dir, "py.sh")
	script := "#!/bin/sh\necho 'boom: bad config' >&2\nexit 1\n"
	if err := os.WriteFile(fakePy, []byte(script), 0o755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	logPath := filepath.Join(dir, "app.log")
	pidPath := filepath.Join(dir, "app.pid")

	pid, err := StartApp(fakePy, filepath.Join(dir, "cfg.yaml"), logPath, pidPath)
	if err == nil {
		t.Fatalf("expected early-crash error")
	}
	if !strings.Contains(err.Error(), "boom") {
		t.Errorf("error should include the log tail, got: %v", err)
	}
	if pid == 0 {
		t.Errorf("PID should be reported even on crash")
	}
	// The PID file is written before the wait.
	if _, statErr := os.Stat(pidPath); statErr != nil {
		t.Errorf("PID file not written: %v", statErr)
	}
}
