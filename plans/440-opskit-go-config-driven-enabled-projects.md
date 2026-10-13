# PLAN: `opskit go` — config-driven enabled-projects list

Closes #440.

## Goal

`opskit go`/`web` must offer **only the user's enabled projects**, read from
`~/.opskit/config.yml`, and must find projects **nested** under `projects_dir`.
Today discovery lists every top-level git repo (102 here) and never recurses, so a
project such as `lfnw/lfnw-django` is invisible and the fzf list is noise.

## Background

#437's Goal promised "any **OpsKit-enabled** project", but the mechanism was never
built: `opskit/_cache.py::read_config()` honours only `projects_dir`, and
`~/.opskit/config.yml` is not created at all. `bin/opskit-projects.py::scan_project_dir`
iterates a single level (`iterdir()`) and accepts any directory with `.git/`.

## Design

### Config file becomes the source of truth

`~/.opskit/config.yml`:

```yaml
projects_dir: /home/user/Projects
projects:
  - Systate
  - BMS
  - lfnw/lfnw-django
```

`projects` is a list of selectors, resolved in this order: absolute path, path
relative to `projects_dir`, basename, `pack.yml` `name`. `_cache.py` gains
`get_projects()`; `read_config()` normalises a missing/null list to `[]`.

### First-run bootstrap

With an empty `projects` list and a TTY, `opskit go` asks whether to scan
`projects_dir` for existing OpsKit projects (those with `.opskit/pack.yml`) and
enable them. On yes it runs `opskit-projects.py bootstrap`; otherwise it reports
that nothing is enabled and exits. Non-TTY callers never block.

### Recursive, bounded discovery

`discover_projects()` walks `projects_dir` (depth ≤ 4), pruning dotdirs, VCS
internals, and build/cache dirs. A directory is a project if it contains `.git/` or
`.opskit/pack.yml`; grouping directories are descended into and matched projects are
not. Git worktrees (`.git` is a file, or a `*-wt-*` name) are skipped by default.
Each record carries a `rel` path so nested projects render and resolve correctly.

### Enabled filter

If `projects` is non-empty, discovery is filtered to matching selectors; unmatched
selectors warn on stderr. If empty, `rescan` records all candidates (so `list` still
shows what exists) — the launcher gates on the bootstrap prompt instead.

### Management + fixes

- `opskit projects bootstrap|add|remove` maintain the list; `list`/`rescan` respect it.
- Launcher: fix the no-op sort condition, replace substring matching with a
  subsequence (fzf-style) match over name/basename/rel, add inline fzf (`--height`),
  and make git detail lazy so scanning no longer shells out to `git` per project
  (the ~19 s `opskit go` delay).
- Cache invalidation also triggers when `config.yml` is newer than the cache.

## Critique

- **Security:** config holds local paths only; atomic writes keep 0600. Selector
  matching is by equality against known fields (no path traversal).
- **Stability:** missing/invalid config tolerated; discovery bounded by depth and a
  prune set; config-mtime invalidation keeps the cache honest.
- **Maintainability:** discovery stays in `opskit-projects.py`; config semantics live
  in `_cache.py` and are imported by both scripts.
- **Effectiveness/Value:** fixes the noise, the nested-match failure, and the scan
  delay together; `opskit go` becomes the "one command" the original plan promised.

## Tests

`tests/test_cache.py` (config round-trip, config-mtime staleness), 
`tests/test_opskit_projects.py` (recursive discovery through a grouping dir,
worktree exclusion, enabled filter, unmatched-selector warning, bootstrap
members-only, add/remove, no git at scan time), `tests/test_tui_matching.py`
(subsequence + nested rel matching). Full suite: `make test`.

## Ready for review
