package install

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestLooksLikeBuildKitCrash(t *testing.T) {
	cases := []struct {
		name   string
		output string
		want   bool
	}{
		{"grpc crash", "ERROR: failed to build: frontend grpc server closed unexpectedly", true},
		{"server eof", "error reading from server: EOF", true},
		{"daemon down", "Cannot connect to the Docker daemon at unix:///var/run/docker.sock", true},
		{"case insensitive", "FRONTEND GRPC SERVER CLOSED UNEXPECTEDLY", true},
		// A genuine Dockerfile/code error must NOT be treated as transient — it
		// would just fail again and mask the real cause.
		{"real build error", "ERROR: process \"/bin/sh -c pip install\" did not complete successfully: exit code 1", false},
		{"compile error", "src/main.go:10: undefined: foo", false},
		{"empty", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := looksLikeBuildKitCrash(tc.output); got != tc.want {
				t.Errorf("looksLikeBuildKitCrash(%q) = %v, want %v", tc.output, got, tc.want)
			}
		})
	}
}

// fakeDocker writes a `docker` shell stub onto PATH that simulates a transient
// BuildKit crash on the FIRST build (printing the grpc-crash signature and
// exiting non-zero), succeeds the `buildx rm`/`buildx create` recovery calls,
// and then either succeeds or fails the retry depending on retrySucceeds. The
// retry runs on the dedicated builder via `docker buildx build --builder …`, so
// both the initial `docker build` and the `docker buildx build` retry count as
// build invocations; a counter file tracks them so the first and second behave
// differently. This exercises buildOne's builder-reset recovery deterministically
// without a real Docker daemon.
func fakeDocker(t *testing.T, retrySucceeds bool) string {
	t.Helper()
	if runtime.GOOS == "windows" {
		t.Skip("shell-stub PATH technique is POSIX-only")
	}
	dir := t.TempDir()
	counter := filepath.Join(dir, "build_count")
	retryExit := "1"
	if retrySucceeds {
		retryExit = "0"
	}
	// `buildx rm`/`buildx create` succeed trivially. A build is either
	// `docker build …` (initial) or `docker buildx build …` (the recovery
	// retry targeting the dedicated builder); both increment the counter. The
	// first build crashes (BuildKit signature); the second returns retryExit.
	script := "#!/bin/sh\n" +
		"is_build=0\n" +
		"if [ \"$1\" = \"build\" ]; then is_build=1\n" +
		"elif [ \"$1\" = \"buildx\" ] && [ \"$2\" = \"build\" ]; then is_build=1\n" +
		"elif [ \"$1\" = \"buildx\" ]; then exit 0\n" +
		"fi\n" +
		"if [ \"$is_build\" = \"1\" ]; then\n" +
		"  n=0; [ -f '" + counter + "' ] && n=$(cat '" + counter + "')\n" +
		"  n=$((n+1)); echo $n > '" + counter + "'\n" +
		"  if [ \"$n\" -eq 1 ]; then\n" +
		"    echo 'ERROR: failed to build: frontend grpc server closed unexpectedly' 1>&2\n" +
		"    exit 1\n" +
		"  fi\n" +
		"  echo 'build ok'\n" +
		"  exit " + retryExit + "\n" +
		"fi\n" +
		"exit 0\n"
	docker := filepath.Join(dir, "docker")
	if err := os.WriteFile(docker, []byte(script), 0o755); err != nil {
		t.Fatalf("write docker stub: %v", err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
	return counter
}

func TestBuildOneRecoversFromBuildKitCrash(t *testing.T) {
	counter := fakeDocker(t, true) // builder reset + retry succeeds

	var buf strings.Builder
	p := BuildPlan{SourceDir: t.TempDir()}
	if err := p.buildOne(&buf, []string{"build", "-t", "x", "."}); err != nil {
		t.Fatalf("buildOne should recover after a builder reset, got: %v", err)
	}
	out := buf.String()
	if !strings.Contains(out, "recreating the build builder") {
		t.Errorf("expected builder-reset notice in output:\n%s", out)
	}
	if !strings.Contains(out, "buildx create") {
		t.Errorf("expected the recovery to recreate the buildx builder:\n%s", out)
	}
	// The retry must target the dedicated builder explicitly rather than switch
	// the operator's default with `--use`.
	if strings.Contains(out, "--use") {
		t.Errorf("recovery must not run `buildx ... --use` (clobbers the operator's default):\n%s", out)
	}
	if !strings.Contains(out, "buildx build --builder "+recoveryBuilderName) {
		t.Errorf("expected the retry to target the recovery builder via --builder:\n%s", out)
	}
	// --load is required so the container-driver builder exports the tagged image
	// to the local store for the next build step / compose up to find.
	if !strings.Contains(out, "--load") {
		t.Errorf("expected the retry to pass --load so the image lands in the local store:\n%s", out)
	}
	if got, _ := os.ReadFile(counter); strings.TrimSpace(string(got)) != "2" {
		t.Errorf("expected exactly 2 build invocations (crash + retry), got %q", string(got))
	}
}

func TestBuildxArgsForBuilder(t *testing.T) {
	got := buildxArgsForBuilder([]string{"build", "-f", "app.Dockerfile", "-t", "x", "."}, "jentic-recovery")
	want := []string{"buildx", "build", "--builder", "jentic-recovery", "--load", "-f", "app.Dockerfile", "-t", "x", "."}
	if strings.Join(got, " ") != strings.Join(want, " ") {
		t.Errorf("buildxArgsForBuilder() = %v, want %v", got, want)
	}
	// A non-`build` invocation is returned unchanged (best-effort).
	pass := []string{"compose", "up", "-d"}
	if out := buildxArgsForBuilder(pass, "jentic-recovery"); strings.Join(out, " ") != strings.Join(pass, " ") {
		t.Errorf("buildxArgsForBuilder() altered a non-build invocation: %v", out)
	}
}

func TestBuildOnePersistentFailureIsActionable(t *testing.T) {
	fakeDocker(t, false) // retry also fails

	var buf strings.Builder
	p := BuildPlan{SourceDir: t.TempDir()}
	err := p.buildOne(&buf, []string{"build", "-t", "x", "."})
	if err == nil {
		t.Fatal("expected a persistent failure error")
	}
	msg := err.Error()
	for _, want := range []string{"not a jentic bug", "restart Docker Desktop", "docker buildx rm"} {
		if !strings.Contains(msg, want) {
			t.Errorf("actionable error missing %q:\n%s", want, msg)
		}
	}
}

func TestBuildOneRealErrorNotRetried(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell-stub PATH technique is POSIX-only")
	}
	// A genuine build error (no transient signature) must surface immediately,
	// without a legacy-builder retry that would mask the true cause.
	dir := t.TempDir()
	script := "#!/bin/sh\necho 'ERROR: process \"/bin/sh -c false\" did not complete successfully: exit code 1' 1>&2\nexit 1\n"
	docker := filepath.Join(dir, "docker")
	if err := os.WriteFile(docker, []byte(script), 0o755); err != nil {
		t.Fatalf("write docker stub: %v", err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	var buf strings.Builder
	p := BuildPlan{SourceDir: t.TempDir()}
	err := p.buildOne(&buf, []string{"build", "-t", "x", "."})
	if err == nil {
		t.Fatal("expected the real build error to surface")
	}
	if strings.Contains(buf.String(), "retrying once with the legacy builder") {
		t.Errorf("a real build error must NOT trigger a legacy retry:\n%s", buf.String())
	}
	if strings.Contains(err.Error(), "not a jentic bug") {
		t.Errorf("a real build error must not be reported as a BuildKit fault: %v", err)
	}
}
