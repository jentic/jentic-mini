package install

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

// assertValidComposeYAML fails the test if data is not parseable YAML with a
// top-level services map (a minimal sanity check on the template's whitespace).
func assertValidComposeYAML(t *testing.T, data []byte) {
	t.Helper()
	var doc map[string]any
	if err := yaml.Unmarshal(data, &doc); err != nil {
		t.Fatalf("rendered compose is not valid YAML: %v\n%s", err, data)
	}
	if _, ok := doc["services"].(map[string]any); !ok {
		t.Fatalf("rendered compose has no services map:\n%s", data)
	}
}

func composeConfigFor(dir string) ComposeConfig {
	return ComposeConfig{
		ComposePath:    filepath.Join(dir, "docker-compose.yaml"),
		ConfigHostPath: filepath.Join(dir, "jentic-one.yaml"),
		LogsHostDir:    filepath.Join(dir, "logs"),
	}
}

func TestMigrateArgsDisablesTTY(t *testing.T) {
	args := migrateArgs("/home/u/.jentic/docker-compose.yaml")
	got := strings.Join(args, " ")

	// -T must precede the service name so `docker compose run` does not try to
	// allocate a pseudo-TTY (which fails when the CLI runs it with no terminal).
	want := "compose -p " + composeProjectName + " -f /home/u/.jentic/docker-compose.yaml run --rm -T " +
		composeServiceApp + " python -m jentic_one.migrations.run"
	if got != want {
		t.Errorf("migrateArgs =\n  %q\nwant\n  %q", got, want)
	}
}

func TestRenderComposeSQLite(t *testing.T) {
	d := NewDraft()
	d.RuntimePath = RuntimeDocker
	d.Apps = []string{"registry", "admin"}
	cfg := composeConfigFor("/home/u/.jentic")

	data, err := RenderCompose(d, cfg)
	if err != nil {
		t.Fatalf("RenderCompose: %v", err)
	}
	assertValidComposeYAML(t, data)
	out := string(data)

	for _, want := range []string{
		AppImageTag,
		"JENTIC_CONFIG_FILE: " + containerConfigPath,
		"JENTIC__APPS: registry,admin",
		// The model cache must be redirected to a writable dir (uid 999's $HOME
		// is not writable) or the ingest embedding stage dies with EACCES.
		"HF_HOME: /tmp/hf-cache",
		"SENTENCE_TRANSFORMERS_HOME: /tmp/hf-cache",
		cfg.ConfigHostPath + ":" + containerConfigPath + ":ro",
		// SQLite is backed by a named volume, not a host bind mount.
		composeDataVolume + ":" + containerDataDir,
		// The broker runs as its own service with apps=broker on its own port.
		composeServiceBroker + ":",
		"JENTIC__APPS: broker",
		"JENTIC__SERVER__PORT: \"" + DefaultBrokerPort + "\"",
		"\"" + DefaultBrokerPort + ":" + DefaultBrokerPort + "\"",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("compose (sqlite) missing %q:\n%s", want, out)
		}
	}
	// The named volume must be declared at the top level.
	if !strings.Contains(out, "volumes:\n  "+composeDataVolume+":") {
		t.Errorf("sqlite compose should declare the %s named volume:\n%s", composeDataVolume, out)
	}
	// The project name must be pinned so volume names don't drift with the
	// install directory (and the uninstall hint stays correct).
	if !strings.Contains(out, "name: "+composeProjectName+"\n") {
		t.Errorf("compose should pin the project name %q:\n%s", composeProjectName, out)
	}
	if got := DataVolumeNames(false); len(got) != 1 || got[0] != composeProjectName+"_"+composeDataVolume {
		t.Errorf("DataVolumeNames(false) = %v, want [%s_%s]", got, composeProjectName, composeDataVolume)
	}
	if got := DataVolumeNames(true); len(got) != 1 || got[0] != composeProjectName+"_"+postgresDataVolume {
		t.Errorf("DataVolumeNames(true) = %v, want [%s_%s]", got, composeProjectName, postgresDataVolume)
	}
	if strings.Contains(out, "pgvector") || strings.Contains(out, "depends_on") {
		t.Errorf("sqlite compose should not include a db service:\n%s", out)
	}
}

func TestRenderComposePostgres(t *testing.T) {
	d := NewDraft()
	d.RuntimePath = RuntimeDocker
	d.DBBackend = BackendPostgres
	d.PGPort = "55432"
	cfg := composeConfigFor("/home/u/.jentic")

	data, err := RenderCompose(d, cfg)
	if err != nil {
		t.Fatalf("RenderCompose: %v", err)
	}
	assertValidComposeYAML(t, data)
	out := string(data)

	for _, want := range []string{
		pgvectorImage,
		"depends_on",
		"condition: service_healthy",
		"\"55432:5432\"",
		cfg.InitSchemasPath() + ":/docker-entrypoint-initdb.d/init-schemas.sql:ro",
		"volumes:\n  db-data:",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("compose (postgres) missing %q:\n%s", want, out)
		}
	}
	// Postgres uses the managed db service, not the SQLite named volume.
	if strings.Contains(out, composeDataVolume) {
		t.Errorf("postgres compose should not reference the SQLite volume:\n%s", out)
	}
}

func TestWriteComposeArtifactsSQLite(t *testing.T) {
	dir := t.TempDir()
	d := NewDraft()
	d.RuntimePath = RuntimeDocker
	cfg := composeConfigFor(dir)

	if err := WriteComposeArtifacts(d, cfg); err != nil {
		t.Fatalf("WriteComposeArtifacts: %v", err)
	}
	if _, err := os.Stat(cfg.ComposePath); err != nil {
		t.Errorf("compose file not written: %v", err)
	}
	if _, err := os.Stat(cfg.LogsHostDir); err != nil {
		t.Errorf("logs dir not created: %v", err)
	}
	// SQLite lives in a named volume (no host data dir) and needs no init SQL.
	if _, err := os.Stat(cfg.InitSchemasPath()); err == nil {
		t.Errorf("sqlite install should not write init-schemas.sql")
	}
}

func TestWriteComposeArtifactsPostgresWritesInitSQL(t *testing.T) {
	dir := t.TempDir()
	d := NewDraft()
	d.RuntimePath = RuntimeDocker
	d.DBBackend = BackendPostgres
	cfg := composeConfigFor(dir)

	if err := WriteComposeArtifacts(d, cfg); err != nil {
		t.Fatalf("WriteComposeArtifacts: %v", err)
	}
	sql, err := os.ReadFile(cfg.InitSchemasPath())
	if err != nil {
		t.Fatalf("init-schemas.sql not written: %v", err)
	}
	for _, schema := range []string{"registry", "control", "admin"} {
		if !strings.Contains(string(sql), "CREATE SCHEMA IF NOT EXISTS "+schema) {
			t.Errorf("init SQL missing schema %q:\n%s", schema, sql)
		}
	}
}
