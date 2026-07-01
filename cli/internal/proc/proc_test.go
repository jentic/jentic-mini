package proc

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

func TestFileExists(t *testing.T) {
	dir := t.TempDir()
	f := filepath.Join(dir, "f.txt")
	if FileExists(f) {
		t.Errorf("missing file reported as existing")
	}
	if err := os.WriteFile(f, []byte("x"), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
	if !FileExists(f) {
		t.Errorf("existing file reported as missing")
	}
	if FileExists(dir) {
		t.Errorf("directory should not count as a regular file")
	}
}

func TestReadPIDFile(t *testing.T) {
	dir := t.TempDir()

	if _, err := ReadPIDFile(filepath.Join(dir, "none")); err == nil {
		t.Errorf("expected error for missing PID file")
	}

	good := filepath.Join(dir, "good.pid")
	if err := os.WriteFile(good, []byte(" 4321\n"), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
	pid, err := ReadPIDFile(good)
	if err != nil {
		t.Fatalf("ReadPIDFile: %v", err)
	}
	if pid != 4321 {
		t.Errorf("pid = %d, want 4321", pid)
	}

	bad := filepath.Join(dir, "bad.pid")
	if err := os.WriteFile(bad, []byte("not-a-number"), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
	if _, err := ReadPIDFile(bad); err == nil {
		t.Errorf("expected parse error for non-numeric PID")
	}
}

func TestAliveAndWaitForExit(t *testing.T) {
	cmd := exec.Command("sleep", "30")
	if err := cmd.Start(); err != nil {
		t.Skipf("cannot start sleep: %v", err)
	}
	t.Cleanup(func() { _ = cmd.Process.Kill(); _, _ = cmd.Process.Wait() })

	if !Alive(cmd.Process) {
		t.Fatalf("running process should be alive")
	}

	// Kill it and confirm WaitForExit observes the exit. Reap in the background
	// so the process leaves the OS process table.
	_ = cmd.Process.Kill()
	go func() { _, _ = cmd.Process.Wait() }()

	if !WaitForExit(cmd.Process, 3*time.Second) {
		t.Fatalf("WaitForExit should report exit after kill")
	}
}
