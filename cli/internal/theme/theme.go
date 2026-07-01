// Package theme is the single source of truth for the Jentic CLI's colour
// scheme. The palette is the company brand from the frontend theme
// (github.com/jentic/jentic-frontend-theme, ui/src/index.css accent tokens), so
// the CLI matches the web app. Every surface — help screen, install wizard, and
// command output — styles through this package.
package theme

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Brand palette — hex values lifted straight from the company theme.
var (
	Brand  = lipgloss.Color("#A3CACC") // primary teal
	Orange = lipgloss.Color("#FDBD79")
	Yellow = lipgloss.Color("#F1E38B")
	Green  = lipgloss.Color("#5EDEB9") // mint
	Pink   = lipgloss.Color("#EDADAF")
	Blue   = lipgloss.Color("#68BAEC")
	Red    = lipgloss.Color("#DB3B0F")
	Muted  = lipgloss.Color("#689296") // primary-500 grey-teal
	White  = lipgloss.Color("#FFFFFF")
)

// Selection glyphs (radio style): a filled ring marks the active/selected
// item, a hollow ring the inactive ones. Shared by the wizard hub menu and
// the huh form selects so selection looks identical everywhere.
const (
	SelectOn  = "◉"
	SelectOff = "○"
)

// Shared styles. Use these instead of constructing one-off lipgloss styles so
// colour usage stays consistent across commands.
var (
	Heading = lipgloss.NewStyle().Bold(true).Foreground(Brand)
	Step    = lipgloss.NewStyle().Bold(true).Foreground(Yellow)
	Command = lipgloss.NewStyle().Foreground(Green)
	Dim     = lipgloss.NewStyle().Foreground(Muted)
	Success = lipgloss.NewStyle().Bold(true).Foreground(Green)
	Warn    = lipgloss.NewStyle().Foreground(Orange)
	Error   = lipgloss.NewStyle().Bold(true).Foreground(Red)
	Info    = lipgloss.NewStyle().Foreground(Blue)
	Accent  = lipgloss.NewStyle().Foreground(Yellow)
)

// Successf renders a printf-formatted string in the success style.
func Successf(format string, a ...any) string { return Success.Render(fmt.Sprintf(format, a...)) }

// Warnf renders a printf-formatted string in the warning style.
func Warnf(format string, a ...any) string { return Warn.Render(fmt.Sprintf(format, a...)) }

// Infof renders a printf-formatted string in the info style.
func Infof(format string, a ...any) string { return Info.Render(fmt.Sprintf(format, a...)) }

// Dimf renders a printf-formatted string in the dim style.
func Dimf(format string, a ...any) string { return Dim.Render(fmt.Sprintf(format, a...)) }

// Headingf renders a printf-formatted string in the heading style.
func Headingf(format string, a ...any) string { return Heading.Render(fmt.Sprintf(format, a...)) }

// Field renders an aligned "label: value" pair with a muted label and a
// brand-coloured value, for the key/value listings commands print.
func Field(label, value string) string {
	return Dim.Render(fmt.Sprintf("%-9s ", label+":")) + lipgloss.NewStyle().Foreground(White).Render(value)
}

// logoLines is the "jentic" figlet (standard font). Kept as plain strings so
// each row can be tinted independently for a vertical gradient.
var logoLines = []string{
	"   _            _   _      ",
	"  (_) ___ _ __ | |_(_) ___ ",
	"  | |/ _ \\ '_ \\| __| |/ __|",
	"  | |  __/ | | | |_| | (__ ",
	" _/ |\\___|_| |_|\\__|_|\\___|",
	"|__/                       ",
}

// logoColors is the top-to-bottom gradient applied across the logo rows.
var logoColors = []lipgloss.Color{Blue, Green, Brand, Yellow, Orange, Pink}

// Logo renders the gradient "jentic" wordmark. Used by the help screen and the
// install wizard so the brand mark is consistent everywhere.
func Logo() string {
	var b strings.Builder
	for i, ln := range logoLines {
		c := logoColors[i%len(logoColors)]
		b.WriteString(lipgloss.NewStyle().Foreground(c).Bold(true).Render(ln))
		b.WriteByte('\n')
	}
	return b.String()
}

// LogoHeader renders the gradient wordmark with an optional block of status
// lines (e.g. version info) pinned to the top-right within totalWidth. When the
// terminal is too narrow to fit both (or rightLines is empty / width unknown),
// it falls back to just the logo. The returned string ends in a single newline.
func LogoHeader(totalWidth int, rightLines []string) string {
	logo := strings.TrimRight(Logo(), "\n")
	if len(rightLines) == 0 {
		return logo + "\n"
	}

	right := lipgloss.JoinVertical(lipgloss.Left, rightLines...)
	gap := totalWidth - lipgloss.Width(logo) - lipgloss.Width(right)
	if totalWidth <= 0 || gap < 2 {
		return logo + "\n"
	}

	spacer := strings.Repeat(" ", gap)
	return lipgloss.JoinHorizontal(lipgloss.Top, logo, spacer, right) + "\n"
}

// VersionPanel formats the CLI and server versions as a single left-to-right
// status line for LogoHeader to pin flush against the right edge. The server
// segment shows the reported version when running, "running" if it is up but
// reports no version, or a dim "offline" when it is not reachable.
func VersionPanel(cliVersion, serverVersion string, serverRunning bool) []string {
	label := func(s string) string { return Dim.Render(s + " ") }

	cli := label("cli") + Accent.Render(orValue(cliVersion, "dev"))

	var server string
	if serverRunning {
		server = label("server") + Command.Render(orValue(serverVersion, "running"))
	} else {
		server = label("server") + Dim.Render("offline")
	}

	return []string{cli + Dim.Render("   ") + server}
}

// orValue returns v, or fallback when v is empty.
func orValue(v, fallback string) string {
	if strings.TrimSpace(v) == "" {
		return fallback
	}
	return v
}
