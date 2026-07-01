package theme

import (
	"strings"
	"testing"
)

func TestFieldContainsLabelAndValue(t *testing.T) {
	got := Field("profile", "work")
	if !strings.Contains(got, "profile") || !strings.Contains(got, "work") {
		t.Errorf("Field = %q, want label+value", got)
	}
}

func TestSelectGlyphsAreRadioRings(t *testing.T) {
	if SelectOn != "◉" || SelectOff != "○" {
		t.Errorf("select glyphs = %q/%q, want ◉/○", SelectOn, SelectOff)
	}
}

func TestLogoHasAllRows(t *testing.T) {
	logo := Logo()
	if lines := strings.Count(logo, "\n"); lines != len(logoLines) {
		t.Errorf("Logo rendered %d rows, want %d", lines, len(logoLines))
	}
}

func TestFormattersNonEmpty(t *testing.T) {
	if Successf("ok %d", 1) == "" || Infof("x") == "" || Warnf("x") == "" || Dimf("x") == "" || Headingf("x") == "" {
		t.Errorf("formatters should render non-empty strings")
	}
}

func TestVersionPanelRunningShowsServerVersion(t *testing.T) {
	lines := VersionPanel("1.2.3", "4.5.6", true)
	if len(lines) != 1 {
		t.Fatalf("VersionPanel returned %d lines, want 1 (left-to-right)", len(lines))
	}
	for _, want := range []string{"cli", "1.2.3", "server", "4.5.6"} {
		if !strings.Contains(lines[0], want) {
			t.Errorf("panel line = %q, want it to contain %q", lines[0], want)
		}
	}
}

func TestVersionPanelOfflineWhenNotRunning(t *testing.T) {
	lines := VersionPanel("1.2.3", "", false)
	if !strings.Contains(lines[0], "offline") {
		t.Errorf("panel line = %q, want offline", lines[0])
	}
}

func TestVersionPanelRunningWithoutVersionSaysRunning(t *testing.T) {
	lines := VersionPanel("dev", "", true)
	if !strings.Contains(lines[0], "running") {
		t.Errorf("panel line = %q, want running fallback", lines[0])
	}
}

func TestLogoHeaderFallsBackToLogoWhenNarrow(t *testing.T) {
	panel := VersionPanel("1.0.0", "2.0.0", true)
	// Width 1 cannot fit logo + panel, so we expect just the logo rows.
	got := LogoHeader(1, panel)
	if lines := strings.Count(got, "\n"); lines != len(logoLines) {
		t.Errorf("narrow LogoHeader rendered %d rows, want logo-only (%d)", lines, len(logoLines))
	}
}

func TestLogoHeaderEmbedsPanelWhenWide(t *testing.T) {
	panel := VersionPanel("1.0.0", "2.0.0", true)
	got := LogoHeader(120, panel)
	if !strings.Contains(got, "1.0.0") || !strings.Contains(got, "2.0.0") {
		t.Errorf("wide LogoHeader = %q, want embedded version panel", got)
	}
}
