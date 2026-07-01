package cmd

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/x/term"
	"github.com/jentic/jentic-one/cli/internal/config"
	"github.com/jentic/jentic-one/cli/internal/install"
	"github.com/jentic/jentic-one/cli/internal/skillgen"
	"github.com/jentic/jentic-one/cli/internal/theme"
	"github.com/spf13/cobra"
)

// errOperatorAndAll is returned when --operator and --all are combined; they
// are mutually exclusive rather than silently letting --all win.
var errOperatorAndAll = errors.New("--operator and --all are mutually exclusive; pass one or the other")

// skillOptions are shared across the skill subcommands.
type skillOptions struct {
	baseURL   string
	operators []string
	scope     string
	force     bool
	yes       bool
	dryRun    bool
	all       bool
	json      bool
}

func newSkillCmd(app *App) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "skill",
		Short: "Generate the Jentic CLI-usage skill into your agent's native layout",
		Long: "skill writes a \"how to use Jentic via the CLI\" skill into each supported\n" +
			"agent runtime's native layout — a dedicated SKILL.md for claude-code,\n" +
			"cursor, and hermes, or a spliced block in AGENTS.md for codex and generic —\n" +
			"so the agent knows the platform loop (register -> request access ->\n" +
			"search/inspect/execute) without you hand-writing anything.\n\n" +
			"Writes are idempotent: generated content lives in a clearly-marked managed\n" +
			"block, so re-running never clobbers your own edits around it.",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			// Bare `jentic skill` behaves like `skill init`.
			return app.skillInit(cmd, &skillOptions{})
		},
	}
	cmd.AddCommand(newSkillInitCmd(app))
	cmd.AddCommand(newSkillListCmd(app))
	cmd.AddCommand(newSkillRemoveCmd(app))
	return cmd
}

func newSkillInitCmd(app *App) *cobra.Command {
	opts := &skillOptions{}
	cmd := &cobra.Command{
		Use:   "init",
		Short: "Generate the Jentic skill for one or more operators",
		Long: "init detects which agent runtimes you have, lets you pick the targets\n" +
			"(or pass --operator), and writes the Jentic CLI-usage skill into each\n" +
			"one's native layout.",
		Example: "  jentic skill init\n" +
			"  jentic skill init --operator claude,cursor\n" +
			"  jentic skill init --all --yes\n" +
			"  jentic skill init --operator generic --dry-run",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return app.skillInit(cmd, opts)
		},
	}
	cmd.Flags().StringSliceVar(&opts.operators, "operator", nil, "operators to target (repeatable or comma-separated)")
	cmd.Flags().StringVar(&opts.scope, "scope", "", "placement scope: user or project (default: per-operator)")
	cmd.Flags().BoolVar(&opts.force, "force", false, "overwrite a managed block you have manually edited")
	cmd.Flags().BoolVar(&opts.yes, "yes", false, "skip the interactive picker (use --operator/--all)")
	cmd.Flags().BoolVar(&opts.dryRun, "dry-run", false, "print target paths without writing")
	cmd.Flags().BoolVar(&opts.all, "all", false, "target every supported operator")
	cmd.Flags().StringVar(&opts.baseURL, "base-url", "", "Jentic control-plane base URL")
	return cmd
}

func newSkillListCmd(app *App) *cobra.Command {
	opts := &skillOptions{}
	cmd := &cobra.Command{
		Use:   "list",
		Short: "Show supported operators and which are detected in this environment",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return app.skillList(cmd, opts)
		},
	}
	cmd.Flags().BoolVar(&opts.json, "json", false, "force JSON output")
	return cmd
}

func newSkillRemoveCmd(app *App) *cobra.Command {
	opts := &skillOptions{}
	cmd := &cobra.Command{
		Use:   "remove",
		Short: "Remove the managed Jentic skill from one or more operators",
		Example: "  jentic skill remove --operator cursor\n" +
			"  jentic skill remove --operator cursor --dry-run\n" +
			"  jentic skill remove --all --force",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return app.skillRemove(cmd, opts)
		},
	}
	cmd.Flags().StringSliceVar(&opts.operators, "operator", nil, "operators to clean up (repeatable or comma-separated)")
	cmd.Flags().StringVar(&opts.scope, "scope", "", "placement scope: user or project (default: per-operator)")
	cmd.Flags().BoolVar(&opts.all, "all", false, "remove from every supported operator")
	cmd.Flags().BoolVar(&opts.force, "force", false, "remove even a managed block you have manually edited")
	cmd.Flags().BoolVar(&opts.dryRun, "dry-run", false, "print what would be removed without deleting anything")
	return cmd
}

// detectEnv builds the detection environment from the real OS, with PATH and
// filesystem probes wired to the standard library. It errors if home or working
// directory cannot be resolved, since every target path is rooted at one of
// them and proceeding with empty bases would write files to surprising places.
func detectEnv() (skillgen.DetectEnv, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return skillgen.DetectEnv{}, fmt.Errorf("resolve home directory: %w", err)
	}
	cwd, err := os.Getwd()
	if err != nil {
		return skillgen.DetectEnv{}, fmt.Errorf("resolve working directory: %w", err)
	}
	return skillgen.DetectEnv{
		Home: home,
		Cwd:  cwd,
		Lookup: func(name string) bool {
			_, err := exec.LookPath(name)
			return err == nil
		},
		Stat: func(path string) bool {
			_, err := os.Stat(path)
			return err == nil
		},
	}, nil
}

// resolveScope maps the --scope flag to a skillgen.Scope (empty = per-operator
// default).
func resolveScope(flag string) (skillgen.Scope, error) {
	switch strings.ToLower(strings.TrimSpace(flag)) {
	case "":
		return "", nil
	case "user":
		return skillgen.ScopeUser, nil
	case "project":
		return skillgen.ScopeProject, nil
	default:
		return "", fmt.Errorf("invalid --scope %q (want \"user\" or \"project\")", flag)
	}
}

// canonicalContent loads the bundled skill, stamped with the resolved base URL.
// The hosted (#277) source is wired here later; for now it always uses bundled.
func (a *App) canonicalContent(baseURLFlag string) (skillgen.Canonical, error) {
	cfg, err := config.Load(a.Paths)
	baseURL := config.DefaultBaseURL
	if err == nil {
		baseURL = cfg.ResolvedBaseURLOr(baseURLFlag)
	} else if baseURLFlag != "" {
		baseURL = baseURLFlag
	}
	return skillgen.Bundled(baseURL)
}

// chooseAdapters resolves the target adapters from flags + detection + an
// interactive picker. It returns the selected adapters or an error.
func (a *App) chooseAdapters(reg *skillgen.Registry, env skillgen.DetectEnv, opts *skillOptions) ([]skillgen.Adapter, error) {
	if opts.all && len(opts.operators) > 0 {
		return nil, errOperatorAndAll
	}
	if opts.all {
		return reg.Adapters(), nil
	}
	if len(opts.operators) > 0 {
		resolved, unknown := reg.ResolveAll(opts.operators)
		if len(unknown) > 0 {
			return nil, fmt.Errorf("unknown operator(s): %s (supported: %s)",
				strings.Join(unknown, ", "), strings.Join(reg.Names(), ", "))
		}
		return resolved, nil
	}

	// No explicit selection. On a non-TTY (or --yes) we cannot prompt.
	if opts.yes || !term.IsTerminal(os.Stdin.Fd()) {
		return nil, errors.New("no operators given; pass --operator <names> or --all (no terminal to prompt)")
	}
	return a.pickOperators(reg, env)
}

// pickOperators runs the interactive multi-select with detected operators
// pre-checked.
func (a *App) pickOperators(reg *skillgen.Registry, env skillgen.DetectEnv) ([]skillgen.Adapter, error) {
	detected := map[skillgen.Operator]bool{}
	for _, d := range reg.Detected(env) {
		detected[d.Operator()] = true
	}

	var selected []string
	optsList := make([]huh.Option[string], 0, len(reg.Adapters()))
	for _, ad := range reg.Adapters() {
		name := string(ad.Operator())
		label := name
		if detected[ad.Operator()] {
			label += " (detected)"
			selected = append(selected, name)
		}
		optsList = append(optsList, huh.NewOption(label, name))
	}

	form := install.NewForm(huh.NewGroup(
		huh.NewMultiSelect[string]().
			Title("Generate the Jentic skill for which operators?").
			Description("Detected runtimes are pre-selected. Space toggles, Enter confirms.").
			Options(optsList...).
			Value(&selected),
	))
	if err := form.Run(); err != nil {
		return nil, err
	}
	if len(selected) == 0 {
		fmt.Fprintln(a.Out, theme.Dim.Render("No operators selected."))
		return nil, nil
	}
	resolved, _ := reg.ResolveAll(selected)
	return resolved, nil
}

func (a *App) skillInit(_ *cobra.Command, opts *skillOptions) error {
	scope, err := resolveScope(opts.scope)
	if err != nil {
		return err
	}
	reg := skillgen.DefaultRegistry()
	env, err := detectEnv()
	if err != nil {
		return err
	}

	adapters, err := a.chooseAdapters(reg, env, opts)
	if err != nil {
		return err
	}
	if len(adapters) == 0 {
		return nil
	}

	return a.writeSkill(adapters, env, scope, opts)
}

// writeSkill renders the canonical skill into each adapter and prints the
// per-operator outcome plus a closing hint. It is the shared body of
// `skill init` and `bootstrap` so both report writes identically. Adapters are
// resolved by the caller (so selection errors surface before any side effects).
func (a *App) writeSkill(adapters []skillgen.Adapter, env skillgen.DetectEnv, scope skillgen.Scope, opts *skillOptions) error {
	content, err := a.canonicalContent(opts.baseURL)
	if err != nil {
		return err
	}
	fmt.Fprintln(a.Out, theme.Heading.Render("Jentic skill"))

	var wrote int
	for _, ad := range adapters {
		out, aerr := skillgen.Apply(ad, content, env, skillgen.ApplyOptions{
			Scope:  scope,
			Force:  opts.force,
			DryRun: opts.dryRun,
		})
		if aerr != nil {
			fmt.Fprintln(a.Out, "  "+theme.Warnf("%s: %v", ad.Operator(), aerr))
			continue
		}
		a.reportOutcome(out, opts.dryRun)
		if out.Changed && !opts.dryRun {
			wrote++
		}
	}

	if opts.dryRun {
		fmt.Fprintln(a.Out, theme.Dim.Render("Dry run — nothing was written."))
		return nil
	}
	if wrote > 0 {
		fmt.Fprintln(a.Out)
		fmt.Fprintln(a.Out, theme.Dim.Render("Your agent picks the skill up on its next start. Re-run after a Jentic update to refresh."))
	}
	return nil
}

// reportOutcome prints a single adapter's result line.
func (a *App) reportOutcome(out skillgen.Outcome, dryRun bool) {
	rel := prettyPath(out.Path)
	switch {
	case out.UserEdits:
		fmt.Fprintln(a.Out, "  "+theme.Warnf("%-8s %s — manual edits detected; re-run with --force to overwrite", out.Operator, rel))
	case dryRun:
		verb := "would update"
		if out.Created {
			verb = "would create"
		}
		fmt.Fprintln(a.Out, "  "+theme.Infof("%-8s %s %s", out.Operator, verb, rel))
	case out.Skipped:
		fmt.Fprintln(a.Out, "  "+theme.Dimf("%-8s %s — already up to date", out.Operator, rel))
	case out.Created:
		fmt.Fprintln(a.Out, "  "+theme.Successf("%-8s created %s", out.Operator, rel))
	default:
		fmt.Fprintln(a.Out, "  "+theme.Successf("%-8s updated %s", out.Operator, rel))
	}
}

func (a *App) skillList(cmd *cobra.Command, opts *skillOptions) error {
	reg := skillgen.DefaultRegistry()
	env, err := detectEnv()
	if err != nil {
		return err
	}
	detected := map[skillgen.Operator]bool{}
	for _, d := range reg.Detected(env) {
		detected[d.Operator()] = true
	}

	if jsonOrPretty(cmd, opts.json) {
		return a.skillListJSON(reg, env, detected)
	}

	fmt.Fprintln(a.Out, theme.Heading.Render("Supported operators"))
	for _, ad := range reg.Adapters() {
		glyph := theme.Dim.Render(theme.SelectOff)
		tag := ""
		if detected[ad.Operator()] {
			glyph = theme.Success.Render(theme.SelectOn)
			tag = " " + theme.Dim.Render("(detected)")
		}
		fmt.Fprintln(a.Out, glyph+" "+theme.Accent.Render(string(ad.Operator()))+tag)
		fmt.Fprintln(a.Out, "    "+theme.Field("target", prettyPath(ad.Target(ad.DefaultScope(), env))))
	}
	return nil
}

func (a *App) skillListJSON(reg *skillgen.Registry, env skillgen.DetectEnv, detected map[skillgen.Operator]bool) error {
	type row struct {
		Operator string `json:"operator"`
		Detected bool   `json:"detected"`
		Target   string `json:"target"`
		Scope    string `json:"scope"`
	}
	rows := make([]row, 0, len(reg.Adapters()))
	for _, ad := range reg.Adapters() {
		rows = append(rows, row{
			Operator: string(ad.Operator()),
			Detected: detected[ad.Operator()],
			Target:   ad.Target(ad.DefaultScope(), env),
			Scope:    string(ad.DefaultScope()),
		})
	}
	return writeJSON(a.Out, map[string]any{"operators": rows})
}

func (a *App) skillRemove(_ *cobra.Command, opts *skillOptions) error {
	scope, err := resolveScope(opts.scope)
	if err != nil {
		return err
	}
	reg := skillgen.DefaultRegistry()
	env, err := detectEnv()
	if err != nil {
		return err
	}

	var adapters []skillgen.Adapter
	switch {
	case opts.all && len(opts.operators) > 0:
		return errOperatorAndAll
	case opts.all:
		adapters = reg.Adapters()
	case len(opts.operators) > 0:
		resolved, unknown := reg.ResolveAll(opts.operators)
		if len(unknown) > 0 {
			return fmt.Errorf("unknown operator(s): %s (supported: %s)",
				strings.Join(unknown, ", "), strings.Join(reg.Names(), ", "))
		}
		adapters = resolved
	default:
		return errors.New("no operators given; pass --operator <names> or --all")
	}

	fmt.Fprintln(a.Out, theme.Heading.Render("Remove Jentic skill"))
	var blocked int
	for _, ad := range adapters {
		out, rerr := skillgen.Remove(ad, env, skillgen.RemoveOptions{
			Scope:  scope,
			Force:  opts.force,
			DryRun: opts.dryRun,
		})
		switch {
		case rerr != nil:
			fmt.Fprintln(a.Out, "  "+theme.Warnf("%-8s %v", ad.Operator(), rerr))
		case out.UserEdits:
			blocked++
			fmt.Fprintln(a.Out, "  "+theme.Warnf("%-8s %s — manual edits detected; re-run with --force to remove", ad.Operator(), prettyPath(out.Path)))
		case out.Missing:
			fmt.Fprintln(a.Out, "  "+theme.Dimf("%-8s nothing to remove (%s)", ad.Operator(), prettyPath(out.Path)))
		case opts.dryRun:
			fmt.Fprintln(a.Out, "  "+theme.Infof("%-8s would remove from %s", ad.Operator(), prettyPath(out.Path)))
		case out.Removed:
			fmt.Fprintln(a.Out, "  "+theme.Successf("%-8s removed from %s", ad.Operator(), prettyPath(out.Path)))
		}
	}
	if opts.dryRun {
		fmt.Fprintln(a.Out, theme.Dim.Render("Dry run — nothing was removed."))
	}
	if blocked > 0 {
		fmt.Fprintln(a.Out, theme.Dim.Render("Re-run with --force to remove blocks you have edited."))
	}
	return nil
}

// prettyPath shortens an absolute path under $HOME to a ~-relative form for
// display.
func prettyPath(p string) string {
	home, err := os.UserHomeDir()
	if err == nil && home != "" {
		if rel, rerr := filepath.Rel(home, p); rerr == nil && !strings.HasPrefix(rel, "..") {
			return filepath.Join("~", rel)
		}
	}
	return p
}
