package install

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestVenvPython(t *testing.T) {
	got := VenvPython("/venv")
	var want string
	if runtime.GOOS == "windows" {
		want = filepath.Join("/venv", "Scripts", "python.exe")
	} else {
		want = filepath.Join("/venv", "bin", "python")
	}
	if got != want {
		t.Errorf("VenvPython = %q, want %q", got, want)
	}
}

func TestBuildPlanVenvPython(t *testing.T) {
	p := BuildPlan{VenvDir: "/v"}
	if p.VenvPython() != VenvPython("/v") {
		t.Errorf("BuildPlan.VenvPython mismatch")
	}
}

func TestPlanLocalBuildInsideRepo(t *testing.T) {
	t.Setenv(SrcEnv, "")
	root := makeFakeRepo(t)
	chdir(t, root)

	plan := PlanLocalBuild("/venv", "/clone")
	if plan.FromGit {
		t.Errorf("inside a repo, build should use local source not git")
	}
	if plan.SourceDir != root {
		t.Errorf("SourceDir = %q, want repo root %q", plan.SourceDir, root)
	}
}

func TestPlanLocalBuildOutsideRepo(t *testing.T) {
	t.Setenv(SrcEnv, "")
	chdir(t, t.TempDir())

	plan := PlanLocalBuild("/venv", "/clone")
	if !plan.FromGit {
		t.Errorf("outside a repo, build should clone from git")
	}
	if plan.SourceDir != "/clone" {
		t.Errorf("SourceDir = %q, want clone dir", plan.SourceDir)
	}
	if plan.GitURL != GitURL {
		t.Errorf("GitURL = %q", plan.GitURL)
	}
}

// TestPlanLocalBuildSrcEnvOverride pins the source via $JENTIC_SRC from a
// non-repo cwd: the build must use that checkout (not clone), regardless of
// where the binary runs.
func TestPlanLocalBuildSrcEnvOverride(t *testing.T) {
	root := makeFakeRepo(t)
	chdir(t, t.TempDir()) // cwd is NOT a repo
	t.Setenv(SrcEnv, root)

	plan := PlanLocalBuild("/venv", "/clone")
	if plan.FromGit {
		t.Errorf("with %s set to a checkout, build should use it, not clone", SrcEnv)
	}
	if plan.SourceDir != root {
		t.Errorf("SourceDir = %q, want %s value %q", plan.SourceDir, SrcEnv, root)
	}
}

// TestPlanLocalBuildSrcEnvInvalid ignores a $JENTIC_SRC that is not a real
// checkout and falls back to the normal cwd-walk / clone behaviour.
func TestPlanLocalBuildSrcEnvInvalid(t *testing.T) {
	chdir(t, t.TempDir())
	t.Setenv(SrcEnv, t.TempDir()) // exists but lacks repo markers

	plan := PlanLocalBuild("/venv", "/clone")
	if !plan.FromGit {
		t.Errorf("an invalid %s should be ignored, falling back to clone", SrcEnv)
	}
}

func TestEnsureUvNoopWhenPresent(t *testing.T) {
	// Stub a `uv` on PATH so EnsureUv takes its fast path and runs no installer.
	dir := t.TempDir()
	uv := filepath.Join(dir, "uv")
	if runtime.GOOS == "windows" {
		uv += ".exe"
	}
	if err := os.WriteFile(uv, []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatalf("write uv stub: %v", err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	var buf strings.Builder
	EnsureUv(&buf)
	if buf.Len() != 0 {
		t.Errorf("EnsureUv wrote output when uv already present: %q", buf.String())
	}
}

func TestRepoRootDetection(t *testing.T) {
	t.Setenv(SrcEnv, "")
	root := makeFakeRepo(t)
	// From a nested subdirectory, RepoRoot should walk up to the marker.
	sub := filepath.Join(root, "a", "b")
	if err := os.MkdirAll(sub, 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	chdir(t, sub)

	got, ok := RepoRoot()
	if !ok {
		t.Fatalf("RepoRoot not found")
	}
	if got != root {
		t.Errorf("RepoRoot = %q, want %q", got, root)
	}
}

// makeFakeRepo creates a directory that looks like a jentic-one checkout.
func makeFakeRepo(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	// EvalSymlinks so macOS /var -> /private/var matches os.Getwd later.
	resolved, err := filepath.EvalSymlinks(root)
	if err == nil {
		root = resolved
	}
	if err := os.MkdirAll(filepath.Join(root, "src", "jentic_one"), 0o755); err != nil {
		t.Fatalf("mkdir src: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, "pyproject.toml"), []byte(`name = "jentic-one"`+"\n"), 0o600); err != nil {
		t.Fatalf("write pyproject: %v", err)
	}
	return root
}

// chdir changes into dir for the duration of the test and restores afterwards.
func chdir(t *testing.T, dir string) {
	t.Helper()
	prev, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatalf("chdir: %v", err)
	}
	t.Cleanup(func() { _ = os.Chdir(prev) })
}
