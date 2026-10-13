#!/usr/bin/env python3
"""
opskit-go.py — TUI project launcher for opencode.

Usage:
  opskit-go.py [project_name]

If project_name is provided:
  - Exact match: skip TUI, launch directly
  - Fuzzy match: if exactly 1 match, skip TUI; if multiple, show TUI
  - No match: error with suggestions

If no project_name:
  - Show TUI for project selection

TUI flow:
  1. Select project via fzf fuzzy search
  2. Review project details on confirmation screen
  3. Press Enter to launch, Ctrl+C to cancel

Launch sequence:
  1. opskit-skills.py setup
  2. opskit-secrets.py bitwarden-session
  3. Record last-used timestamp
  4. cd <project> && exec opencode
"""

import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
_OPSKIT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(_OPSKIT_ROOT))

from opskit._cache import (
    CONFIG_FILE,
    read_discovery_projects,
    cache_is_stale,
    get_last_used_order,
    update_last_used,
    get_projects_dir,
    get_projects,
)


def ensure_cache():
    """Rescan the projects dir if the cache is missing or stale."""
    projects_dir = get_projects_dir()
    if not read_discovery_projects() or cache_is_stale(projects_dir):
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-projects.py"), "rescan"],
            capture_output=True, text=True,
        )


def ensure_enabled():
    """Guarantee a non-empty enabled list; offer to bootstrap on first run."""
    if get_projects():
        return True

    if not sys.stdin.isatty():
        print(
            "No projects enabled. Run 'opskit projects bootstrap' or "
            "'opskit projects add <path>'.",
            file=sys.stderr,
        )
        return False

    print(f"No projects enabled in {CONFIG_FILE}.")
    try:
        answer = input(
            f"Scan {get_projects_dir()} for OpsKit projects (.opskit/pack.yml) "
            "and enable them? [y/N] "
        )
    except EOFError:
        return False

    if answer.strip().lower() not in ("y", "yes"):
        print("Nothing enabled. Add projects with 'opskit projects add <path>'.")
        return False

    subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "opskit-projects.py"), "bootstrap"],
        check=False,
    )
    return bool(get_projects())


def sort_projects_by_last_used(projects):
    """Sort projects by last-used timestamp (most recent first)."""
    project_map = {p["path"]: p for p in projects}

    sorted_projects = []
    seen = set()
    for path in get_last_used_order():
        if path in project_map and path not in seen:
            sorted_projects.append(project_map[path])
            seen.add(path)

    # Append projects not present in the last-used cache.
    for proj in projects:
        if proj["path"] not in seen:
            sorted_projects.append(proj)
            seen.add(proj["path"])

    return sorted_projects


def _subsequence_score(query, target):
    """Score query as a subsequence of target, or None if it isn't one.

    Rewards consecutive runs and word-boundary hits (fzf-style) so that
    'group' prefers 'group/nested-app' over an incidental scatter of letters.
    """
    qi = 0
    score = 0
    last = -2
    for i, ch in enumerate(target):
        if qi < len(query) and ch == query[qi]:
            score += 1
            if last == i - 1:
                score += 2
            if i == 0 or target[i - 1] in "/-_. ":
                score += 3
            last = i
            qi += 1
            if qi == len(query):
                return score
    return None


def _project_targets(proj):
    return [
        proj.get("name", "").lower(),
        Path(proj.get("path", "")).name.lower(),
        (proj.get("rel", "") or "").lower(),
    ]


def fuzzy_match_projects(name, projects):
    """Fuzzy (subsequence) match a query against name / basename / rel path.

    Returns matching project dicts, best score first.
    """
    query = name.strip().lower()
    if not query:
        return []

    scored = []
    for proj in projects:
        best = None
        for target in _project_targets(proj):
            s = _subsequence_score(query, target)
            if s is not None and (best is None or s > best):
                best = s
        if best is not None:
            scored.append((best, proj))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [proj for _, proj in scored]


def _git_info(path):
    """(branch, status) computed on demand — the scan never shells out to git."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path, capture_output=True, text=True, timeout=10,
        ).stdout.strip() or "detached"
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path, capture_output=True, text=True, timeout=10,
        )
        return branch, ("dirty" if status.stdout.strip() else "clean")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "unknown", "unknown"


PICKER_NAME_W = 28
PICKER_BRANCH_W = 18
PICKER_STATUS_W = 8


def _pad(value, width):
    """Left-justify to a fixed width, truncating long values with an ellipsis."""
    if len(value) > width:
        value = value[: width - 1] + "…"
    return f"{value:<{width}}"


def _picker_header():
    return (
        f"{'NAME':<{PICKER_NAME_W}} {'BRANCH':<{PICKER_BRANCH_W}} "
        f"{'STATUS':<{PICKER_STATUS_W}} RESUME"
    )


def _picker_row(proj, git_lookup):
    """One fixed-width display row: NAME | BRANCH | STATUS | RESUME."""
    name = proj.get("rel") or proj.get("name", "unknown")
    path = proj.get("path", "")
    branch, status = git_lookup(path) if path else ("unknown", "unknown")
    resume = "[resume]" if proj.get("has_resume") else ""
    return (
        f"{_pad(name, PICKER_NAME_W)} {_pad(branch, PICKER_BRANCH_W)} "
        f"{_pad(status, PICKER_STATUS_W)} {resume}"
    ).rstrip()


def build_picker(projects, git_lookup=_git_info):
    """Return (header, lines) for the fzf picker.

    Each line is ``"<path>\\t<display>"``: field 1 is the selection value
    (returned via fzf ``--accept-nth=1``), field 2 is the aligned display.
    """
    lines = [
        f"{proj.get('path', '')}\t{_picker_row(proj, git_lookup)}"
        for proj in projects
    ]
    return _picker_header(), lines


def display_project_info(proj):
    """Display project info for the confirmation screen."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Project: {proj.get('name', 'unknown')}")
    lines.append(f"Path: {proj.get('path', 'unknown')}")
    lines.append("")

    if proj.get("description"):
        lines.append(f"Description: {proj['description']}")
    lines.append(f"Classification: {proj.get('classification', 'unknown')}")
    branch, status = _git_info(proj.get("path", ""))
    lines.append(f"Git: {branch} ({status})")

    if proj.get("has_resume"):
        lines.append("Resume: has RESUME.md")
    else:
        lines.append("Resume: no RESUME.md")

    lines.append("")
    lines.append("Press Enter to launch opencode, Ctrl+C to cancel")
    lines.append("=" * 60)
    return "\n".join(lines)


def run_openskill_setup():
    """Run opskit-skills.py setup (non-blocking, best-effort)."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-skills.py"), "setup"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


def get_bw_session():
    """Get BW_SESSION via opskit-secrets.py."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-secrets.py"), "bitwarden-session"],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def launch_project(project_path):
    """Launch opencode in the given project path."""
    # 1. Setup skills (best-effort)
    run_openskill_setup()

    # 2. Get BW_SESSION
    bw_session = get_bw_session()

    # 3. Update last-used
    update_last_used(project_path)

    # 4. Set up environment and exec opencode
    env = os.environ.copy()
    if bw_session:
        env["BW_SESSION"] = bw_session

    # Change to project directory and exec opencode
    os.chdir(project_path)
    env["OPSKIT_PROJECT_PATH"] = project_path

    try:
        os.execvpe("opencode", ["opencode"], env)
    except FileNotFoundError:
        print(f"Error: opencode not found on PATH", file=sys.stderr)
        sys.exit(1)


def run_fzf_selection(projects):
    """Run fzf to let the user select a project. Returns selected path or None.

    No timeout: this is an interactive picker, not a batch call. Esc/Ctrl+C
    cancels (nonzero fzf exit) and returns None.
    """
    header, lines = build_picker(projects)
    input_data = "\n".join(lines) + "\n" if lines else ""

    try:
        fzf_proc = subprocess.run(
            [
                "fzf",
                "--height=40%",
                "--reverse",
                "--prompt=opskit> ",
                "--delimiter=\t",
                "--with-nth=2",   # display the aligned columns (field 2)
                "--accept-nth=1",  # return only the path (field 1)
                f"--header={header}",
            ],
            input=input_data,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        print("Error: fzf not found", file=sys.stderr)
        sys.exit(1)

    if fzf_proc.returncode != 0:
        return None  # User cancelled (Esc/Ctrl+C)

    selected = fzf_proc.stdout.strip()
    if not selected:
        return None
    # --accept-nth=1 yields the path; split anyway so we still work if a
    # build ignores --accept-nth and returns the whole line.
    return selected.split("\t")[0]


def main():
    parser = argparse.ArgumentParser(description="Launch opencode in an opskit project")
    parser.add_argument("project", nargs="?", help="Project name or path (optional)")

    args = parser.parse_args()

    # First run with no enabled projects: offer to scan for OpsKit members.
    if not ensure_enabled():
        sys.exit(0)

    # Cache-first: rescan only when the cache is missing or stale.
    ensure_cache()
    projects = read_discovery_projects()
    if not projects:
        print("No projects found. Run: opskit projects rescan")
        sys.exit(1)

    # Sort by last-used
    projects = sort_projects_by_last_used(projects)

    if args.project:
        # Try exact match first
        exact_match = None
        for proj in projects:
            proj_name = proj.get("name", "")
            proj_path = proj.get("path", "")
            proj_rel = proj.get("rel", "")
            if (proj_name == args.project or proj_rel == args.project
                    or proj_path == args.project or proj_path.endswith(args.project)):
                exact_match = proj
                break

        if exact_match:
            # Exact match — launch directly
            launch_project(exact_match["path"])
        else:
            # Try fuzzy match
            matches = fuzzy_match_projects(args.project, projects)
            if len(matches) == 1:
                # Single fuzzy match — launch directly
                launch_project(matches[0]["path"])
            elif len(matches) > 1:
                # Multiple matches — show TUI
                selected_path = run_fzf_selection(matches)
                if selected_path:
                    launch_project(selected_path)
                else:
                    print("No project selected")
                    sys.exit(0)
            else:
                print(f"No project matches '{args.project}'", file=sys.stderr)
                names = [p.get("name", "") for p in projects]
                close = difflib.get_close_matches(args.project, names, n=5, cutoff=0.3)
                if not close:
                    close = names[:5]
                print("Suggestions:", file=sys.stderr)
                for suggestion in close:
                    print(f"  {suggestion}", file=sys.stderr)
                sys.exit(1)
    else:
        # No project specified — show TUI
        selected_path = run_fzf_selection(projects)
        if selected_path:
            # Find the full project info
            proj_info = None
            for proj in projects:
                if proj.get("path") == selected_path:
                    proj_info = proj
                    break

            if proj_info:
                # Show confirmation screen
                print(display_project_info(proj_info))
                try:
                    input("Press Enter to launch...")
                except EOFError:
                    pass
                launch_project(selected_path)
            else:
                launch_project(selected_path)
        else:
            print("No project selected")
            sys.exit(0)


if __name__ == "__main__":
    main()
