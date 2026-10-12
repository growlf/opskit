# PLAN: `opskit go` — TUI project launcher with opencode integration

## Goal

Add `opskit go` and `opskit web` commands to launch opencode in any OpsKit-enabled project via a fuzzy-search TUI, with per-project preferences stored in `~/.opskit/`, secrets passthru interface, and skill symlink management — all without cluttering repos or requiring network access.

## Scope

### In scope

- `opskit go [<project>]` — TUI launcher for `opencode`
- `opskit web` — `opencode web --mdns` wrapper
- `opskit skills setup|verify|cleanup` — symlink management for `~/.config/opencode/skills/` and `~/.agents/skills/`
- `opskit-secrets.py` — secrets engine router (reads `~/.opskit/secrets.yml`, calls `bin/bwunlock.sh`)
- `~/.opskit/last-used.json` — per-project usage tracking for sort order
- Shell completion updates for new subcommands

### Out of scope (next task)

- Full skill catalog system with metadata
- Smart suggestions / learning ladder research
- Multi-engine secrets implementations (interface only, bitwarden via existing `bwunlock.sh`)
- Multi-engine ticketing (workflow) implementations (Vikunja, Github, Gitlab)
- Separating out all other tool choices to be agnosticly supported as much as possible.

## Design

### Project discovery

- Config path stored in `~/.opskit/config.yml`: `projects_dir: ~/Projects` (asked during install, default ~/Projects)
- Cache is the source of truth (`~/.opskit/last-discovery.json`)
- Cache invalidation: cache is stale if `last-discovery.json` is older than 24 hours, or if the projects_dir mtime has changed since the cache was written
- `opskit go` reads from cache (instant, no scanning)
- Cache is stale/missing → scans projects dir, saves cache
- `opskit projects rescan` — force full rescan
- `opskit projects add <path>` — add a single project to cache without rescanning
- `opskit projects list` — show cached projects
- Scan reads: name, description, classification from `pack.yml`; git status --porcelain (local only); existence of `RESUME.md`
- Sort: by `~/.opskit/last-used.json` timestamps (most recent first)
- Skip: dotdirs, `.git`, `.venv`, non-project dirs (skip any entry matching `.*` or not containing `.git/` or `pack.yml`)

### TUI (when no project name or fuzzy match is ambiguous)

Two-step flow:

1. **Select** — `fzf` fuzzy search through cached project list, user selects one project
2. **Review & Accept** — Show full project details (description, classification, git branch, git status, RESUME indicator, last-used time) in a confirmation screen. User presses Enter to launch, Ctrl+C to cancel

fzf receives project data via stdin as one-line-per-project (`name\tpath`), sorted by last-used timestamp. Selection is the project path.

### Matching (when project name provided)

- Exact match → skip TUI, launch directly
- Fuzzy match → if exactly 1 match, skip TUI; if multiple, show TUI
- No match → error with suggestions

### Launch sequence (in order)

1. `opskit-skills.py setup` — idempotent, creates symlinks, reports changes
2. `opskit-secrets.py bitwarden-session` — resolves engine from `~/.opskit/projects/<name>/secrets.yml` or global `~/.opskit/secrets.yml`, calls `bin/bwunlock.sh`, outputs `BW_SESSION`
3. Record last-used timestamp (atomic write via temp file + rename)
4. `cd <project> && exec opencode`

### `opskit web` (in order)

1. `opskit-skills.py setup` (same as go)
2. `opskit-secrets.py bitwarden-session` (same as go)
3. `exec opencode web --mdns`

### Secrets passthru

- `~/.opskit/secrets.yml` (global fallback):
  
  ```yaml
  engine: bitwarden
  ```

- `~/.opskit/projects/<name>/secrets.yml` (per-project override)

- `opskit-secrets.py <secret_name>` routes to:
  
  - `bitwarden` → calls `~/Projects/opskit/bin/bwunlock.sh`, reads session
  - `env` → reads from environment variable specified in config
  - Unknown engine → prints error, exits 1

- BW_SESSION token is visible in `/proc/<pid>/environ` (same as running opencode in a terminal) — documented as known risk, no practical alternative without opencode support for `--session-file`

### Skill symlinks

- Source: `~/Projects/opskit/.opencode/skills/` (resolved from OPSKIT_ROOT env var or git rev-parse)
- `opskit-skills.py setup`:
  - Creates symlinks in `~/.config/opencode/skills/` (flat, each skill as top-level symlink)
  - Creates `~/.agents/skills/opskit/` (subdirectory, each skill as subdirectory symlink)
  - Idempotent — skips if symlink exists and points to correct target
  - Reports what was created/updated/skipped
  - On conflict (existing symlink/file pointing elsewhere): refuses, reports; `--force` to skip
- `opskit-skills.py verify`: checks all symlinks point to valid SKILL.md files
- `opskit-skills.py cleanup`: removes only opskit-managed symlinks (identified by target path), reports what was removed

### Shared cache module

- `opskit/_cache.py` — shared Python module for all cache operations
  - `read_cache()` → loads `last-discovery.json`, returns parsed data
  - `write_cache(data)` → atomic write (tempfile + rename) to `last-discovery.json`
  - `read_last_used()` → loads `last-used.json`
  - `update_last_used(project_path)` → atomic update of last-used entry
  - `get_project_from_cache(path)` → look up project details by path
  - `cache_is_stale(projects_dir)` → check if cache is older than 24h or projects_dir mtime changed
  - All file I/O uses tempfile + rename pattern for atomicity and concurrent-write safety
  - All scripts (`go.py`, `projects.py`) import from `_cache.py`, never read/write JSON directly

### File structure (new files)

```
opskit/bin/opskit-go.py          # Main TUI launcher (thin dispatcher)
opskit/bin/opskit-skills.py      # Symlink management
opskit/bin/opskit-web.py         # Web wrapper
opskit/bin/opskit-secrets.py     # Secrets router
opskit/bin/opskit-projects.py    # Projects cache (rescan/add/list dispatcher)
opskit/_cache.py                 # Shared cache read/write module
opskit/...
```

No changes to existing files except adding subcommand dispatch in main `opskit` script and updating shell completion scripts (bash and zsh) for new subcommands.

### `~/.opskit/` directory (checked on every opskit invocation)

Every opskit command checks for `~/.opskit/` at startup. If it doesn't exist or is missing key files, opskit detects the gap and offers to run a full configuration check/recovery. This ensures graceful recovery if a user deletes the folder or migrates systems. Directory is created with mode 0700.

```
~/.opskit/
  config.yml          # projects_dir, tui preference
  last-used.json      # {version: 1, entries: [{project_path, timestamp}]} — LRU rotation, max 100 entries
  last-discovery.json # {version: 1, timestamp: "...", projects_dir: "...", projects: [{name, path, ...}]}
  secrets.yml         # Global secrets engine: bitwarden
  projects/
    <project-name>/
      secrets.yml     # Per-project secrets engine override (optional)
```

### `last-used.json` structure

```json
{
  "version": 1,
  "entries": [
    {
      "project_path": "/home/netyeti/Projects/Phoenix",
      "timestamp": "2026-10-11T14:30:00"
    }
  ]
}
```

- Entries are kept in LRU order, max 100 entries
- On update: move existing entry to end of list (or append if new), trim if over 100

### `~/.opskit/` directory permissions

Created with `os.makedirs(~/.opskit/, mode=0o700, exist_ok=True)` on first use. All files within created with `umask 0077` or explicit `os.chmod(..., 0o600)`.

### Path normalization

All project paths are canonicalized using `pathlib.Path.resolve()` before storage in cache or last-used.json. Symlinked project directories are resolved to their real paths to ensure consistent lookups.

### `pack.yml` missing during scan

If a directory contains `.git/` but no `pack.yml`:

- Use directory name as project name (as-is, no slugification)
- Use "public" as default classification
- Use git remote name as description if available
- Skip the project if neither `pack.yml` nor git remote is available

### Shell completion updates

- Bash: add `go`, `web`, `skills`, `projects` to `_opskit_completion` function in `opskit` script
- Zsh: add to `_opskit()` function in zsh completion block in `opskit` script

## Implementation steps

1. **_cache.py** — Create shared cache module with read/write/atomic-update/cache-stale-check
2. **opskit-projects.py** — Create with `rescan`, `add`, `list`, `config` subcommands (uses _cache.py)
3. **opskit-skills.py** — Create with `setup`, `verify`, `cleanup` subcommands
4. **opskit-secrets.py** — Create with engine routing (bitwarden → bwunlock.sh, env → env var)
5. **opskit-go.py** — Create with TUI (fzf select → review/accept → launch), uses _cache.py
6. **opskit-web.py** — Create as thin wrapper calling go's setup + `opencode web --mdns`
7. **opskit (main)** — Add `go`, `web`, `skills`, `projects` subcommands to argparser
8. **opskit (completion)** — Update bash and zsh completion scripts for new subcommands
9. **install.sh / check** — Add fzf to dependencies, verify bwunlock.sh + fzf availability
10. **Tests** — Unit tests for:
    - _cache.py read/write/atomic-update/cache-stale-check
    - Projects rescan/add/list (filesystem ops)
    - Skills setup/verify/cleanup (filesystem ops)
    - Secrets routing (mock bwunlock.sh)
    - TUI matching logic (fzf integration)
    - Cache data structure schema validation
11. **Validation** — `make test`, `bash -n` on all new scripts, functional test

## Critique

**Security:**

- Symlinks in user's home config dirs — low risk, user-controlled location
- Symlink targets validated to be within `~/Projects/opskit/` to prevent path traversal
- bwunlock.sh output (session token) passed via subprocess, never logged
- `~/.opskit/` created with mode 0700, files with 0600
- BW_SESSION visible in `/proc/<pid>/environ` — documented as known risk, same as running opencode directly in a terminal

**Stability:**

- All file I/O is idempotent and atomic (tempfile + rename pattern in _cache.py)
- Cache-first project discovery — scan only on-demand (`rescan`, `add`, or when cache is stale)
- bwunlock.sh failure is non-fatal — session may be empty, opencode still launches
- Concurrent write protection for `last-used.json` via tempfile + rename in _cache.py
- `~/.opskit/` created with 0700 permissions, all files 0600

**Maintainability:**

- Shared cache module (_cache.py) — single source of truth for all cache operations
- Clear separation: router (secrets.py) vs implementation (bwunlock.sh)
- Skills management is isolated and reversible (cleanup)
- TUI uses standard fzf — well-documented, no custom TUI framework
- Cache format versioned (version: 1) for future migration paths

**Effectiveness:**

- Two-step TUI (select → review/accept) — user confirms before launching
- Per-project preferences allow different engines per project
- Skills symlinks make opskit tools available to all agents (opencode, Claude Code, Crush)
- Path normalization ensures consistent lookups across symlinks

**Value:**

- Single command to access any project with full opskit tooling
- TUI is fast (< 1s for 12 projects)
- Lazy skill loading keeps opencode lean
- Secrets passthru is extensible for future engines

**IMPORTANT: After merging, restore stashed changes from main:**

```bash
# Back on main (the primary checkout):
cd ~/Projects/opskit && git stash pop
```

These are pre-existing changes that were stashed before creating this worktree.

## Ready for review
