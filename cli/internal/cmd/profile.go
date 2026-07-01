package cmd

import (
	"errors"
	"fmt"
	"os"
	"slices"
	"sort"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/term"
	"github.com/jentic/jentic-one/cli/internal/config"
	"github.com/jentic/jentic-one/cli/internal/profile"
	"github.com/jentic/jentic-one/cli/internal/theme"
	"github.com/spf13/cobra"
)

func newProfileCmd(app *App) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "profile",
		Short: "View and switch the active profile",
		Long: "profile lists the local agent profiles under ~/.jentic/profiles and\n" +
			"switches which one commands act on by default. The active profile is the\n" +
			"--profile flag, else $JENTIC_PROFILE, else config.yaml default_profile.\n" +
			"Run bare on a terminal to pick interactively.",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return app.profileSwitch(cmd, "")
		},
	}
	cmd.AddCommand(newProfileListCmd(app))
	cmd.AddCommand(newProfileUseCmd(app))
	cmd.AddCommand(newProfileAddKeyCmd(app))
	return cmd
}

func newProfileListCmd(app *App) *cobra.Command {
	return &cobra.Command{
		Use:     "list",
		Aliases: []string{"ls"},
		Short:   "List profiles and mark the active one",
		Args:    cobra.NoArgs,
		RunE: func(_ *cobra.Command, _ []string) error {
			return app.profileList()
		},
	}
}

func newProfileUseCmd(app *App) *cobra.Command {
	return &cobra.Command{
		Use:   "use [name]",
		Short: "Set the default profile (interactive picker when no name given)",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := ""
			if len(args) == 1 {
				name = args[0]
			}
			return app.profileSwitch(cmd, name)
		},
	}
}

// profileList prints every profile with the active one marked by a filled radio
// ring, plus each profile's base URL, agent id, and token state.
func (a *App) profileList() error {
	cfg, err := config.Load(a.Paths)
	if err != nil {
		return err
	}
	names, err := profile.List(a.Paths)
	if err != nil {
		return err
	}

	fmt.Fprintln(a.Out, theme.Heading.Render("Profiles"))
	if len(names) == 0 {
		fmt.Fprintln(a.Out, dotDown()+" "+theme.Dim.Render("no profiles yet — run `jentic register`"))
		return nil
	}

	sort.Strings(names)
	active := cfg.ResolvedProfileName("")
	for _, name := range names {
		a.printProfileRow(name, name == active)
	}
	fmt.Fprintln(a.Out)
	fmt.Fprintln(a.Out, theme.Dim.Render("active: ")+theme.Command.Render(active))
	return nil
}

// printProfileRow renders a single profile: a radio glyph + name header, then an
// indented summary read from its on-disk metadata and cached tokens.
func (a *App) printProfileRow(name string, active bool) {
	glyph := theme.Dim.Render(theme.SelectOff)
	if active {
		glyph = theme.Success.Render(theme.SelectOn)
	}
	fmt.Fprintln(a.Out, glyph+" "+theme.Accent.Render(name))

	p, err := profile.Open(a.Paths, name)
	if err != nil {
		fmt.Fprintln(a.Out, "    "+theme.Warnf("unreadable: %v", err))
		return
	}
	meta, err := p.LoadMeta()
	if err != nil {
		fmt.Fprintln(a.Out, "    "+theme.Warnf("unreadable: %v", err))
		return
	}
	if meta.IsAPIKey() {
		fmt.Fprintln(a.Out, "    "+theme.Field("auth", "api-key"))
		fmt.Fprintln(a.Out, "    "+theme.Field("base_url", valueOr(meta.BaseURL, "-")))
		if meta.AgentID != "" {
			fmt.Fprintln(a.Out, "    "+theme.Field("agent_id", meta.AgentID))
		}
		key, _ := p.LoadAPIKey()
		fmt.Fprintln(a.Out, "    "+theme.Field("key", apiKeyLabel(key)))
		return
	}
	if meta.AgentID == "" {
		fmt.Fprintln(a.Out, "    "+theme.Dim.Render("not registered"))
		return
	}
	fmt.Fprintln(a.Out, "    "+theme.Field("base_url", valueOr(meta.BaseURL, "-")))
	fmt.Fprintln(a.Out, "    "+theme.Field("agent_id", meta.AgentID))
	tokens, _ := p.LoadTokens()
	state, _ := tokenStatus(tokens)
	fmt.Fprintln(a.Out, "    "+theme.Field("token", state))
}

// profileSwitch persists the default profile. With no name it opens the
// interactive picker on a terminal, or errors on a pipe/CI.
func (a *App) profileSwitch(_ *cobra.Command, name string) error {
	cfg, err := config.Load(a.Paths)
	if err != nil {
		return err
	}
	names, err := profile.List(a.Paths)
	if err != nil {
		return err
	}
	if len(names) == 0 {
		return errors.New("no profiles found — run `jentic register` to create one")
	}
	sort.Strings(names)

	if name == "" {
		if !term.IsTerminal(os.Stdin.Fd()) {
			return errors.New("no profile name given; pass one (e.g. `jentic profile use <name>`) or run interactively")
		}
		selected, perr := a.pickProfile(names, cfg.ResolvedProfileName(""))
		if perr != nil {
			if errors.Is(perr, errProfilePickAborted) {
				fmt.Fprintln(a.Out, theme.Dim.Render("Cancelled."))
				return nil
			}
			return perr
		}
		name = selected
	}

	if !slices.Contains(names, name) {
		return fmt.Errorf("profile %q does not exist; run `jentic profile list` to see options", name)
	}

	if err := config.SetDefaultProfile(a.Paths, name); err != nil {
		return err
	}
	fmt.Fprintln(a.Out, theme.Successf("Active profile set to %q", name))
	if env := os.Getenv(config.ProfileEnv); env != "" && env != name {
		fmt.Fprintln(a.Out, theme.Warnf("note: $%s=%q overrides this for the current shell", config.ProfileEnv, env))
	}
	fmt.Fprintln(a.Out, theme.Dim.Render("Override per-command with --profile or $"+config.ProfileEnv+"."))
	return nil
}

// errProfilePickAborted signals the interactive picker was cancelled (q/esc).
var errProfilePickAborted = errors.New("profile selection cancelled")

// pickProfile runs the interactive two-column picker: a list of profiles on the
// left and the highlighted profile's details on the right. It pre-selects the
// active profile and returns the chosen name (or errProfilePickAborted).
func (a *App) pickProfile(names []string, active string) (string, error) {
	items := make([]profileItem, 0, len(names))
	start := 0
	for i, n := range names {
		items = append(items, a.loadProfileItem(n))
		if n == active {
			start = i
		}
	}

	m, err := tea.NewProgram(&profilePicker{items: items, cursor: start, active: active}).Run()
	if err != nil {
		return "", err
	}
	res := m.(*profilePicker)
	if res.aborted {
		return "", errProfilePickAborted
	}
	return res.chosen, nil
}

// profileItem is a profile's display summary, loaded once before the picker runs
// so cursor movement re-renders without touching disk.
type profileItem struct {
	name       string
	registered bool
	apiKey     bool
	baseURL    string
	agentID    string
	agentName  string
	token      string
	keyLabel   string
}

// loadProfileItem reads a profile's metadata and token state for the detail pane.
func (a *App) loadProfileItem(name string) profileItem {
	it := profileItem{name: name}
	p, err := profile.Open(a.Paths, name)
	if err != nil {
		return it
	}
	meta, err := p.LoadMeta()
	if err != nil {
		return it
	}
	if meta.IsAPIKey() {
		it.registered = true
		it.apiKey = true
		it.baseURL = meta.BaseURL
		it.agentID = meta.AgentID
		key, _ := p.LoadAPIKey()
		it.keyLabel = apiKeyLabel(key)
		return it
	}
	if meta.AgentID == "" {
		return it
	}
	it.registered = true
	it.baseURL = meta.BaseURL
	it.agentID = meta.AgentID
	it.agentName = meta.AgentName
	tokens, _ := p.LoadTokens()
	it.token, _ = tokenStatus(tokens)
	return it
}

const profileListWidth = 24

// profilePicker is the Bubble Tea model backing the interactive picker.
type profilePicker struct {
	items   []profileItem
	cursor  int
	active  string
	chosen  string
	aborted bool
	done    bool
}

func (p *profilePicker) Init() tea.Cmd { return nil }

func (p *profilePicker) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	m, ok := msg.(tea.KeyMsg)
	if !ok {
		return p, nil
	}
	switch m.String() {
	case "ctrl+c", "q", "esc":
		p.aborted = true
		p.done = true
		return p, tea.Quit
	case "up", "k":
		if p.cursor > 0 {
			p.cursor--
		}
	case "down", "j":
		if p.cursor < len(p.items)-1 {
			p.cursor++
		}
	case "enter", " ":
		if len(p.items) > 0 {
			p.chosen = p.items[p.cursor].name
		}
		p.done = true
		return p, tea.Quit
	}
	return p, nil
}

func (p *profilePicker) View() string {
	if p.done {
		return ""
	}
	head := theme.Heading.Render("Select active profile") + "\n\n"

	rows := make([]string, 0, len(p.items))
	for i, it := range p.items {
		rows = append(rows, p.row(i, it))
	}
	list := lipgloss.NewStyle().Width(profileListWidth).Render(strings.Join(rows, "\n"))

	detailBox := lipgloss.NewStyle().
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(theme.Muted).
		BorderLeft(true).
		PaddingLeft(2).
		Render(profileDetailView(p.items[p.cursor]))

	body := lipgloss.JoinHorizontal(lipgloss.Top, list, detailBox)
	return head + body + "\n\n" + theme.Dim.Render("↑/↓ move · enter select · q/esc cancel")
}

// row renders one profile in the left list: a filled ring + accent name for the
// hovered row, a hollow ring otherwise, with an "(active)" tag on the persisted one.
func (p *profilePicker) row(i int, it profileItem) string {
	tag := ""
	if it.name == p.active {
		tag = " " + theme.Dim.Render("(active)")
	}
	if i == p.cursor {
		return theme.Success.Render(theme.SelectOn) + " " + theme.Accent.Render(it.name) + tag
	}
	return theme.Dim.Render(theme.SelectOff+" "+it.name) + tag
}

// profileDetailView renders the right-hand details for the hovered profile.
func profileDetailView(it profileItem) string {
	out := theme.Heading.Render(it.name)
	if !it.registered {
		return out + "\n" + theme.Dim.Render("not registered — run `jentic register`")
	}
	if it.apiKey {
		out += "\n" + theme.Field("auth", "api-key")
		out += "\n" + theme.Field("base_url", valueOr(it.baseURL, "-"))
		if it.agentID != "" {
			out += "\n" + theme.Field("agent_id", it.agentID)
		}
		out += "\n" + theme.Field("key", it.keyLabel)
		return out
	}
	out += "\n" + theme.Field("base_url", valueOr(it.baseURL, "-"))
	out += "\n" + theme.Field("agent_id", it.agentID)
	if it.agentName != "" {
		out += "\n" + theme.Field("name", it.agentName)
	}
	out += "\n" + theme.Field("token", it.token)
	return out
}
