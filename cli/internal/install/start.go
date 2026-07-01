package install

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// earlyExitWindow is how long StartApp watches a freshly launched app for an
// immediate crash before considering it healthy. It is a var (not a const) so
// tests can widen it to make crash detection deterministic under load.
var earlyExitWindow = 2 * time.Second

// StartApp launches `<venvPython> -m jentic_one` in the background, detached from
// the installer, with output redirected to logPath and the PID written to
// pidPath. It returns the PID once the app has survived a short startup window;
// if the app exits immediately it returns an error containing the log tail.
func StartApp(venvPython, configPath, logPath, pidPath string) (int, error) {
	return startProcess(venvPython, configPath, logPath, pidPath, nil)
}

// StartBroker launches the broker as its own background process with
// apps=broker on its dedicated port (the broker cannot be bundled with other
// surfaces). It mirrors StartApp but overrides JENTIC__APPS and the server port
// via the environment so it can run alongside the combined app.
func StartBroker(venvPython, configPath, logPath, pidPath, brokerPort string) (int, error) {
	return startProcess(venvPython, configPath, logPath, pidPath, []string{
		"JENTIC__APPS=broker",
		"JENTIC__SERVER__PORT=" + brokerPort,
	})
}

// startProcess launches `<venvPython> -m jentic_one` in the background,
// detached from the installer, with output redirected to logPath, the PID
// written to pidPath, and extraEnv overlaid on the inherited environment. It
// returns the PID once the process has survived a short startup window; if it
// exits immediately it returns an error containing the log tail.
func startProcess(venvPython, configPath, logPath, pidPath string, extraEnv []string) (int, error) {
	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o600) //nolint:gosec // logPath is a CLI-managed file under JENTIC_HOME.
	if err != nil {
		return 0, fmt.Errorf("open app log: %w", err)
	}
	defer logFile.Close()

	cmd := exec.Command(venvPython, "-m", "jentic_one")
	cmd.Env = append(os.Environ(), "JENTIC_CONFIG_FILE="+configPath)
	cmd.Env = append(cmd.Env, extraEnv...)
	cmd.Stdout = logFile
	cmd.Stderr = logFile
	cmd.SysProcAttr = detachSysProcAttr()

	if err := cmd.Start(); err != nil {
		return 0, fmt.Errorf("start app: %w", err)
	}
	pid := cmd.Process.Pid
	_ = os.WriteFile(pidPath, []byte(strconv.Itoa(pid)), 0o600)

	// Watch for an early crash (bad config, port in use, missing DB, ...).
	exited := make(chan error, 1)
	go func() { exited <- cmd.Wait() }()

	select {
	case waitErr := <-exited:
		return pid, fmt.Errorf("app exited during startup (%w)\n%s", waitErr, tailFile(logPath, 20))
	case <-time.After(earlyExitWindow):
		return pid, nil
	}
}

// tailFile returns the last n lines of the file at path (best effort), indented
// for inclusion in an error message.
func tailFile(path string, n int) string {
	data, err := os.ReadFile(path) //nolint:gosec // path is the CLI-managed app log under JENTIC_HOME.
	if err != nil {
		return ""
	}
	lines := strings.Split(strings.TrimRight(string(data), "\n"), "\n")
	if len(lines) > n {
		lines = lines[len(lines)-n:]
	}
	for i, ln := range lines {
		lines[i] = "    " + ln
	}
	return strings.Join(lines, "\n")
}
