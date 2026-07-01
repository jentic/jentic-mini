//go:build !windows

package install

import "syscall"

// detachSysProcAttr starts the app in its own session so it keeps running after
// the installer (its parent) exits.
func detachSysProcAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{Setsid: true}
}
