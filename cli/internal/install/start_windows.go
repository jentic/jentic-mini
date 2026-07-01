//go:build windows

package install

import "syscall"

// detachSysProcAttr is a no-op on Windows (no session concept); the child still
// outlives the installer once it is started without Wait.
func detachSysProcAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{}
}
