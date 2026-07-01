package install

import (
	"fmt"
	"os"
	"strings"

	"github.com/charmbracelet/x/term"
	"github.com/jentic/jentic-one/cli/internal/theme"
)

// minPinnedHeight is the smallest terminal height for which pinning the banner
// is worthwhile; below it we leave the scroll region alone and stream normally.
const minPinnedHeight = 14

// PinnedBanner keeps the jentic banner fixed at the top of the terminal while
// build output scrolls in the region beneath it, using a DECSTBM scroll region.
// When the output is not an interactive terminal it is inert and Stop is a no-op.
type PinnedBanner struct {
	out    *os.File
	height int
	active bool
}

// StartPinnedBanner clears the screen, draws the banner at the top, and confines
// further output to a scroll region below it. It degrades gracefully: if out is
// not a TTY (or is too short) it returns an inert controller and the caller's
// output prints normally.
func StartPinnedBanner(out *os.File) *PinnedBanner {
	p := &PinnedBanner{out: out}

	_, height, err := term.GetSize(out.Fd())
	if err != nil || height < minPinnedHeight {
		return p
	}

	header := theme.Logo() + theme.Dim.Render("  onboarding wizard") + "\n\n"
	top := strings.Count(header, "\n") + 1

	// Clear, home, draw banner, set the scroll region below it, then park the
	// cursor at the top of that region.
	fmt.Fprint(out, "\x1b[2J\x1b[H")
	fmt.Fprint(out, header)
	fmt.Fprintf(out, "\x1b[%d;%dr", top, height)
	fmt.Fprintf(out, "\x1b[%d;1H", top)

	p.height = height
	p.active = true
	return p
}

// Stop releases the scroll region and moves the cursor below it so subsequent
// output (the summary) flows normally.
func (p *PinnedBanner) Stop() {
	if !p.active {
		return
	}
	p.active = false
	fmt.Fprint(p.out, "\x1b[r")                // reset scroll region to full screen
	fmt.Fprintf(p.out, "\x1b[%d;1H", p.height) // cursor to last row
}
