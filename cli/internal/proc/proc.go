// Package proc holds small filesystem/process helpers shared by the start and
// stop commands: reading a PID file, liveness probing, and waiting for exit.
package proc

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// FileExists reports whether path exists and is a regular file.
func FileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

// ReadPIDFile reads and parses the PID stored at path.
func ReadPIDFile(path string) (int, error) {
	data, err := os.ReadFile(path) //nolint:gosec // path is a CLI-managed PID file under JENTIC_HOME, not user input.
	if err != nil {
		return 0, err
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(data)))
	if err != nil {
		return 0, fmt.Errorf("parse PID in %s: %w", path, err)
	}
	return pid, nil
}

// Alive reports whether the process accepts signals (i.e. exists).
func Alive(proc *os.Process) bool {
	return proc.Signal(syscall.Signal(0)) == nil
}

// LivePID reads the PID file at path and reports the recorded process id and
// whether that process is currently running. A missing PID file yields
// (0, false, nil); only a malformed/unreadable file returns an error. A present
// file whose process has exited yields (pid, false, nil) — a stale PID file.
func LivePID(path string) (pid int, alive bool, err error) {
	pid, err = ReadPIDFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return 0, false, nil
		}
		return 0, false, err
	}
	// os.FindProcess never fails on Unix; it returns a usable handle whether or
	// not the process is still alive, so liveness is decided by the signal probe.
	p, _ := os.FindProcess(pid)
	return pid, Alive(p), nil
}

// WaitForExit polls until the process exits or timeout elapses, returning true
// if it exited.
func WaitForExit(proc *os.Process, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if !Alive(proc) {
			return true
		}
		time.Sleep(100 * time.Millisecond)
	}
	return !Alive(proc)
}
