package config

import "testing"

func TestLoadManifestMissingIsNotFound(t *testing.T) {
	paths := Paths{Root: t.TempDir()}
	m, found, err := LoadManifest(paths)
	if err != nil {
		t.Fatalf("LoadManifest error: %v", err)
	}
	if found {
		t.Errorf("found = true for missing manifest, want false")
	}
	if m.ResolvedRepo() != DefaultRepo {
		t.Errorf("ResolvedRepo = %q, want default %q", m.ResolvedRepo(), DefaultRepo)
	}
}

func TestManifestSaveAndLoadRoundTrip(t *testing.T) {
	paths := Paths{Root: t.TempDir()}
	want := &Manifest{
		Repo:       "jentic/jentic-one",
		Ref:        "feat/cli",
		Commit:     "abc1234",
		CLIVersion: "feat/cli",
		BinaryPath: "/tmp/jentic",
	}
	if err := want.Save(paths); err != nil {
		t.Fatalf("Save error: %v", err)
	}
	if want.InstalledAt == "" {
		t.Errorf("Save did not stamp InstalledAt")
	}

	got, found, err := LoadManifest(paths)
	if err != nil || !found {
		t.Fatalf("LoadManifest err=%v found=%v", err, found)
	}
	if got.Ref != "feat/cli" || got.Commit != "abc1234" || got.BinaryPath != "/tmp/jentic" {
		t.Errorf("round-trip mismatch: %+v", got)
	}
}

func TestMergeStackPreservesCLIFields(t *testing.T) {
	paths := Paths{Root: t.TempDir()}
	// Simulate the installer having written the CLI fields first.
	base := &Manifest{Repo: "jentic/jentic-one", Ref: "feat/cli", Commit: "abc1234", BinaryPath: "/tmp/jentic"}
	if err := base.Save(paths); err != nil {
		t.Fatalf("Save base: %v", err)
	}

	m, _, err := LoadManifest(paths)
	if err != nil {
		t.Fatalf("LoadManifest: %v", err)
	}
	if err := m.MergeStack(paths, ModeDocker, "postgres", "8100", "feat/cli", "def5678", "feat/cli"); err != nil {
		t.Fatalf("MergeStack: %v", err)
	}

	got, _, err := LoadManifest(paths)
	if err != nil {
		t.Fatalf("reload: %v", err)
	}
	if got.Mode != ModeDocker || got.DB != "postgres" {
		t.Errorf("stack fields not merged: mode=%q db=%q", got.Mode, got.DB)
	}
	if got.BrokerPort != "8100" {
		t.Errorf("BrokerPort = %q, want 8100", got.BrokerPort)
	}
	if got.Commit != "def5678" {
		t.Errorf("commit = %q, want refreshed def5678", got.Commit)
	}
	if got.BinaryPath != "/tmp/jentic" {
		t.Errorf("BinaryPath = %q, want preserved /tmp/jentic", got.BinaryPath)
	}
}
