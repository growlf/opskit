# PLAN: `opskit go` picker — column layout and no timeout

Closes #442.

## Goal

The fzf picker in `opskit go` must be readable and must not self-terminate.
Two defects:

1. **No columns.** `run_fzf_selection` fed fzf `f"{rel}\t{path}"` with no header and
   no fixed widths, so fzf expanded the tab to a tab stop and the long absolute path
   dominated each line — no column boundaries.
2. **Times out.** fzf was invoked with `timeout=60`; leaving the picker open longer
   killed it, printed "fzf not found or timed out", and exited 1.

## Design

Pure, unit-testable helpers plus a rewritten `run_fzf_selection`:

- `_picker_header()` → header using the same fixed column widths:
  `NAME | BRANCH | STATUS | RESUME`.
- `_picker_row(proj, git_lookup)` → one display row, space-padded to fixed widths,
  long values truncated with `…`; branch/status from `git_lookup(path)`.
- `build_picker(projects, git_lookup=_git_info)` → `(header, lines)`; each line is
  `f"{path}\t{display}"` — field 1 is the selection value, field 2 the display.
- `run_fzf_selection(projects)`:
  - fzf args add `--delimiter=\t --with-nth=2 --accept-nth=1 --header=<header>`
    (display field 2; return field 1 = path; show a header). Keeps
    `--height=40% --reverse --prompt=opskit> `.
  - **no `timeout`** — interactive picker; Esc/Ctrl+C cancels (nonzero rc → `None`).
  - return `stdout.split("\t")[0]`, so it still works on a build that ignores
    `--accept-nth`.
- Branch/dirty are computed lazily via `_git_info` for the displayed rows only.

## Notes from implementation

- fzf `--with-nth` scopes the fuzzy search to the **displayed** columns, so the
  hidden path is not searchable — the visible `NAME` (the `rel` selector) is. Fine.
- `--accept-nth` needs fzf ≥ 0.48 (0.67 here); the defensive split covers older.

## Critique

- **Security:** unchanged input surface (paths from cache/config); argv list, no shell;
  fixed widths, no format injection.
- **Stability:** fzf missing → clear error; empty input handled by the caller; no
  timeout means an interactive wait can never be cut short.
- **Maintainability:** formatting isolated in pure helpers → tested without git/fzf.
- **Effectiveness/Value:** fixes both complaints; no scan-cost regression.
- **Flaw → resolution:** truncating a long name could hide a distinguishing suffix.
  Resolution: `rel` is already the unique-ish selector and we now search it; accepted.

## Tests

`tests/test_tui_picker.py`: header names the columns; header/row column offsets align;
`[resume]` shown only when present; long names truncate to the column width; each line's
field 1 is the path; `run_fzf_selection` passes **no** `timeout` and passes the column
options; cancel and empty selection return `None`. Full suite: `make test`.
