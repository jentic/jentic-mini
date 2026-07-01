package skillgen

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Outcome describes what applying one adapter did, for user-facing messaging
// and for the command's exit reporting.
type Outcome struct {
	Operator  Operator
	Path      string
	Created   bool // the target file did not exist before
	Changed   bool // the managed block was written/updated
	Skipped   bool // nothing to do (already up to date)
	UserEdits bool // an existing managed block had manual edits (needs --force)
}

// ApplyOptions controls how Apply writes a skill.
type ApplyOptions struct {
	Scope  Scope // user vs project; zero value uses the adapter default
	Force  bool  // overwrite a user-edited managed block
	DryRun bool  // compute the outcome and target but write nothing
}

// Apply renders the canonical content through one adapter and writes it to the
// adapter's target, idempotently. It never clobbers user content outside the
// managed block, and refuses to overwrite a manually-edited block unless Force.
func Apply(a Adapter, c Canonical, env DetectEnv, opts ApplyOptions) (Outcome, error) {
	scope := opts.Scope
	if scope == "" {
		scope = a.DefaultScope()
	}
	target := a.Target(scope, env)
	out := Outcome{Operator: a.Operator(), Path: target}

	existing, err := os.ReadFile(target) //nolint:gosec // target is derived from adapter rules + env, not arbitrary input.
	if err != nil && !os.IsNotExist(err) {
		return out, fmt.Errorf("read %s: %w", target, err)
	}
	out.Created = os.IsNotExist(err)

	// Detect a manually-edited existing block before rendering so we can refuse
	// without Force. A malformed/foreign hash is treated as refreshable, not an
	// edit, so a clean re-run can recover it. For whole-file targets the
	// frontmatter lives outside the block, so we also treat a changed
	// frontmatter as a user edit (it would otherwise be silently overwritten).
	norm := []byte(normalizeNewlines(string(existing)))
	if blk := findBlock(norm); blk.found && !opts.Force {
		edited := blockUserEdited(norm, blk)
		if !edited && a.OwnsWholeFile() {
			edited = wholeFileSurroundEdited(a, c, norm, blk)
		}
		if edited {
			out.UserEdits = true
			return out, nil
		}
	}

	newBytes, changed, err := a.Render(c, existing)
	if err != nil {
		return out, fmt.Errorf("render %s skill: %w", a.Operator(), err)
	}
	out.Changed = changed
	out.Skipped = !changed

	if !changed || opts.DryRun {
		return out, nil
	}

	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil { //nolint:gosec // skill dirs are world-readable by design.
		return out, fmt.Errorf("create %s: %w", filepath.Dir(target), err)
	}
	if err := writeFileAtomic(target, newBytes); err != nil {
		return out, fmt.Errorf("write %s: %w", target, err)
	}
	return out, nil
}

// RemoveOptions controls how Remove strips a managed block.
type RemoveOptions struct {
	Scope  Scope // user vs project; zero value uses the adapter default
	Force  bool  // remove even a manually-edited managed block
	DryRun bool  // compute the outcome and target but write nothing
}

// RemoveOutcome describes what removing one adapter's block did, for messaging.
type RemoveOutcome struct {
	Path      string
	Removed   bool // the managed block was stripped (or file deleted)
	Missing   bool // there was no managed block / no file to remove
	UserEdits bool // the block had manual edits and was kept (needs --force)
}

// Remove strips the managed block from an adapter's target. For single-file
// targets it splices the block out (leaving user content); for a target whose
// whole file is ours, removing the only block empties it, so we delete the
// file (and prune now-empty jentic skill dirs). A block whose body the user
// has manually edited is preserved unless opts.Force is set, mirroring Apply's
// edit guard so removal is not silently destructive of in-block changes.
func Remove(a Adapter, env DetectEnv, opts RemoveOptions) (RemoveOutcome, error) {
	scope := opts.Scope
	if scope == "" {
		scope = a.DefaultScope()
	}
	target := a.Target(scope, env)
	out := RemoveOutcome{Path: target}

	existing, err := os.ReadFile(target) //nolint:gosec // target is derived from adapter rules + env.
	if os.IsNotExist(err) {
		out.Missing = true
		return out, nil
	}
	if err != nil {
		return out, fmt.Errorf("read %s: %w", target, err)
	}
	existing = []byte(normalizeNewlines(string(existing)))

	blk := findBlock(existing)
	if !blk.found {
		out.Missing = true
		return out, nil
	}

	// Refuse to delete a block whose body the user has manually edited, unless
	// forced — symmetric with Apply's guard, so `remove` is never a silent way
	// to lose in-block changes. Content *outside* the block (frontmatter,
	// sibling prose) is preserved by the splice below, so it does not block
	// removal.
	if !opts.Force && blockUserEdited(existing, blk) {
		out.UserEdits = true
		return out, nil
	}

	if opts.DryRun {
		out.Removed = true
		return out, nil
	}

	// Compute what remains once the block is excised.
	remainder := trimSurrounding(string(existing[:blk.start]) + string(existing[blk.end:]))

	// A dedicated SKILL.md (claude/hermes) starts life as just our frontmatter
	// plus the block. If nothing but that frontmatter is left we delete the file
	// and prune the dirs we created; but if the user added their own content
	// (extra prose, sibling sections) we must preserve it by rewriting instead.
	if filepath.Base(target) == "SKILL.md" && isOnlyFrontmatter(remainder) {
		if err := os.Remove(target); err != nil {
			return out, fmt.Errorf("remove %s: %w", target, err)
		}
		pruneEmptyDirs(filepath.Dir(target))
		out.Removed = true
		return out, nil
	}

	if remainder == "" {
		if err := os.Remove(target); err != nil {
			return out, fmt.Errorf("remove %s: %w", target, err)
		}
		out.Removed = true
		return out, nil
	}
	if err := writeFileAtomic(target, []byte(remainder+"\n")); err != nil {
		return out, fmt.Errorf("write %s: %w", target, err)
	}
	out.Removed = true
	return out, nil
}

// wholeFileSurroundEdited reports whether the content surrounding the managed
// block in a whole-file target (the frontmatter prelude we write before the
// block, and any suffix after it) was modified by the user. Because that
// surrounding content lives outside the hashed block, a plain block-hash check
// misses these edits, which would then be silently overwritten on refresh. We
// render a fresh canonical file and compare both the pre-block and post-block
// remainders against what's on disk.
func wholeFileSurroundEdited(a Adapter, c Canonical, existing []byte, blk block) bool {
	fresh, _, err := a.Render(c, nil)
	if err != nil {
		return false // can't render to compare; let the refresh proceed.
	}
	freshNorm := []byte(normalizeNewlines(string(fresh)))
	freshBlk := findBlock(freshNorm)
	if !freshBlk.found {
		return false
	}
	existingPrelude := strings.TrimSpace(string(existing[:blk.start]))
	freshPrelude := strings.TrimSpace(string(freshNorm[:freshBlk.start]))
	if existingPrelude != freshPrelude {
		return true
	}
	// The block end offset points just past the end marker line; anything after
	// it is user-added suffix. The freshly rendered dedicated file has no suffix,
	// so any non-empty on-disk suffix is a user edit we must not clobber.
	existingSuffix := strings.TrimSpace(string(existing[blk.end:]))
	freshSuffix := strings.TrimSpace(string(freshNorm[freshBlk.end:]))
	return existingSuffix != freshSuffix
}

// writeFileAtomic writes data to a temp file in the target's directory, then
// renames it over the target. This guarantees a reader never sees a partially
// written file and a crash/disk-full mid-write cannot truncate or corrupt the
// existing target — which matters because some targets (AGENTS.md) interleave
// our managed block with user-owned content. The target's existing mode is
// preserved; new files default to 0o644 (skill files are meant to be read by
// other tools).
func writeFileAtomic(target string, data []byte) error {
	mode := os.FileMode(0o644)
	if info, err := os.Stat(target); err == nil {
		mode = info.Mode().Perm()
	}

	dir := filepath.Dir(target)
	tmp, err := os.CreateTemp(dir, ".jentic-skill-*.tmp")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	// Best-effort cleanup if we bail before the rename succeeds. Once the rename
	// lands, tmpName no longer exists, so skip the spurious remove.
	renamed := false
	defer func() {
		if !renamed {
			_ = os.Remove(tmpName)
		}
	}()

	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Sync(); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	if err := os.Chmod(tmpName, mode); err != nil {
		return err
	}
	if err := os.Rename(tmpName, target); err != nil {
		return err
	}
	renamed = true
	return nil
}

// isOnlyFrontmatter reports whether s consists solely of a single leading
// `---`-delimited YAML frontmatter block (what our dedicated adapters write
// around the managed block) with no other content. Used by Remove to decide
// whether a SKILL.md is purely ours and safe to delete, versus carrying
// user-added content that must be preserved.
func isOnlyFrontmatter(s string) bool {
	s = strings.TrimSpace(s)
	if s == "" {
		return true
	}
	if !strings.HasPrefix(s, "---\n") {
		return false
	}
	rest := s[len("---\n"):]
	end := strings.Index(rest, "\n---")
	if end < 0 {
		return false
	}
	return strings.TrimSpace(rest[end+len("\n---"):]) == ""
}

// trimSurrounding collapses the blank lines left behind when a block is spliced
// out of the middle of a file.
func trimSurrounding(s string) string {
	for len(s) > 0 && (s[0] == '\n') {
		s = s[1:]
	}
	for len(s) > 0 && s[len(s)-1] == '\n' {
		s = s[:len(s)-1]
	}
	return s
}

// maxPruneDepth bounds how far up the tree pruneEmptyDirs will walk; the
// jentic skill dir tree (skills/jentic/<category>) is shallow, so a small cap
// prevents an unbounded climb if a boundary dir is ever missing.
const maxPruneDepth = 4

// pruneEmptyDirs removes dir and any now-empty ancestors that the generator
// itself created (the `jentic/<category>` tree under a skills dir), best-effort.
// It stops at the first non-empty directory or at a boundary dir we did not
// create (.claude, .hermes, skills, …).
func pruneEmptyDirs(dir string) {
	for range maxPruneDepth {
		base := filepath.Base(dir)
		if base == "skills" || base == ".claude" || base == ".hermes" {
			return // reached a boundary we don't own.
		}
		entries, err := os.ReadDir(dir)
		if err != nil || len(entries) > 0 {
			return
		}
		if err := os.Remove(dir); err != nil {
			return
		}
		dir = filepath.Dir(dir)
	}
}
