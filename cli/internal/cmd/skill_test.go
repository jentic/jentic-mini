package cmd

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSkillRegisteredOnAPIRoot(t *testing.T) {
	root := newAPIRootCmd(testApp(t))
	if !hasCommand(root, "skill") {
		t.Fatal("jentic root missing skill command")
	}
	if hasCommand(newCtlRootCmd(testApp(t)), "skill") {
		t.Error("jenticctl should not register skill")
	}
}

// runSkill executes the skill command tree with args in an isolated cwd+home so
// detection and writes never touch the real environment.
func runSkill(t *testing.T, args ...string) (*App, string) {
	t.Helper()
	tmp := t.TempDir()
	t.Setenv("HOME", tmp)
	t.Chdir(tmp)

	out := new(bytes.Buffer)
	app := testApp(t)
	app.Out = out
	app.Err = out

	cmd := newSkillCmd(app)
	cmd.SetOut(out)
	cmd.SetErr(out)
	cmd.SetArgs(args)
	if err := cmd.Execute(); err != nil {
		t.Fatalf("skill %v: %v", args, err)
	}
	return app, out.String()
}

func TestSkillInitGenericWritesManagedBlock(t *testing.T) {
	_, out := runSkill(t, "init", "--operator", "generic", "--yes")
	if !strings.Contains(out, "created") {
		t.Errorf("output missing created line: %q", out)
	}
	cwd, _ := os.Getwd()
	data, err := os.ReadFile(filepath.Join(cwd, "AGENTS.md"))
	if err != nil {
		t.Fatalf("AGENTS.md not written: %v", err)
	}
	if !strings.Contains(string(data), "BEGIN JENTIC MANAGED SKILL") {
		t.Error("managed block sentinel missing")
	}
	if !strings.Contains(string(data), "jentic register") {
		t.Error("skill body missing expected command")
	}
}

func TestSkillInitDryRunWritesNothing(t *testing.T) {
	_, out := runSkill(t, "init", "--operator", "generic", "--dry-run")
	if !strings.Contains(out, "Dry run") {
		t.Errorf("missing dry-run notice: %q", out)
	}
	cwd, _ := os.Getwd()
	if _, err := os.Stat(filepath.Join(cwd, "AGENTS.md")); !os.IsNotExist(err) {
		t.Error("dry run should not write AGENTS.md")
	}
}

func TestSkillInitUnknownOperatorErrors(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("HOME", tmp)
	t.Chdir(tmp)
	app := testApp(t)
	app.Out = new(bytes.Buffer)
	cmd := newSkillCmd(app)
	cmd.SetOut(app.Out)
	cmd.SetErr(app.Out)
	cmd.SetArgs([]string{"init", "--operator", "bogus", "--yes"})
	if err := cmd.Execute(); err == nil {
		t.Fatal("expected error for unknown operator")
	}
}

func TestSkillInitNoOperatorNonInteractiveErrors(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("HOME", tmp)
	t.Chdir(tmp)
	app := testApp(t)
	app.Out = new(bytes.Buffer)
	cmd := newSkillCmd(app)
	cmd.SetOut(app.Out)
	cmd.SetErr(app.Out)
	// --yes with no --operator and no TTY: must error rather than hang.
	cmd.SetArgs([]string{"init", "--yes"})
	if err := cmd.Execute(); err == nil {
		t.Fatal("expected error when no operators and non-interactive")
	}
}

func TestSkillListJSON(t *testing.T) {
	_, out := runSkill(t, "list", "--json")
	var payload struct {
		Operators []struct {
			Operator string `json:"operator"`
			Target   string `json:"target"`
		} `json:"operators"`
	}
	if err := json.Unmarshal([]byte(out), &payload); err != nil {
		t.Fatalf("list --json not valid JSON: %v\n%s", err, out)
	}
	if len(payload.Operators) < 5 {
		t.Errorf("expected >=5 operators, got %d", len(payload.Operators))
	}
}

func TestSkillRemoveNoOperatorErrors(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("HOME", tmp)
	t.Chdir(tmp)
	app := testApp(t)
	app.Out = new(bytes.Buffer)
	cmd := newSkillCmd(app)
	cmd.SetOut(app.Out)
	cmd.SetErr(app.Out)
	cmd.SetArgs([]string{"remove"})
	if err := cmd.Execute(); err == nil {
		t.Fatal("expected error when remove has no operators")
	}
}
