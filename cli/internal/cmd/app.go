package cmd

import (
	"io"
	"os"

	"github.com/jentic/jentic-one/cli/internal/config"
)

// App is the dependency container threaded into every command constructor. It
// holds the resolved filesystem paths and the output streams, so commands carry
// no package-global state and are constructible (and testable) in isolation.
type App struct {
	// Paths resolves every filesystem location the CLI owns.
	Paths config.Paths
	// Out and Err are the standard output streams (overridable in tests).
	Out io.Writer
	Err io.Writer
}

// newApp builds the default application wiring (real paths, os streams).
func newApp() (*App, error) {
	paths, err := config.NewPaths()
	if err != nil {
		return nil, err
	}
	return &App{Paths: paths, Out: os.Stdout, Err: os.Stderr}, nil
}
