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
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
_OPSKIT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(_OPSKIT_ROOT))

from opskit._cache import (
    read_discovery_projects,
    cache_is_stale,
    get_last_used_order,
    update_last_used,
    get_projects_dir,
)


def ensure_cache():
    """Rescan the projects dir if the cache is missing or stale."""
    projects_dir = get_projects_dir()
    if not read_discovery_projects() or cache_is_stale(projects_dir):
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-projects.py"), "rescan"],
            capture_output=True, text=True,
        )


def sort_projects_by_last_used(projects):
    """Sort projects by last-used timestamp (most recent first)."""
    project_map = {p["path"]: p for p in projects}
    last_used_order = get_last_used_order()

    # Projects in last-used order first, then uncached projects
    sorted_projects = []
    for path in last_used_order:
        if path in project_map:
            sorted_projects.append(project_map[path])

    # Add any projects not in last-used
    for proj in projects:
        if proj["path"] not in project_map or proj not in sorted_projects:
            sorted_projects.append(proj)

    return sorted_projects


def fuzzy_match_projects(name, projects):
    """Fuzzy match a project name against the project list.

    Returns a list of matching project dicts.
    """
    name_lower = name.lower()
    matches = []
    for proj in projects:
        proj_name = proj.get("name", "").lower()
        proj_path = proj.get("path", "").lower()
        if name_lower in proj_name or name_lower in proj_path:
            matches.append(proj)
    return matches


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
    lines.append(f"Git: {proj.get('git_branch', '?')} ({proj.get('git_status', '?')})")

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
    """Run fzf to let the user select a project. Returns selected path or None."""
    # Build fzf input: tab-separated name and path, sorted by last-used
    lines = []
    for proj in projects:
        name = proj.get("name", "unknown")
        path = proj.get("path", "")
        # Use path as the selection value
        lines.append(f"{name}\t{path}")

    input_data = "\n".join(lines) + "\n"

    try:
        fzf_proc = subprocess.run(
            ["fzf"],
            input=input_data,
            capture_output=True, text=True, timeout=60,
        )
        if fzf_proc.returncode != 0:
            return None  # User cancelled

        selected = fzf_proc.stdout.strip()
        if not selected:
            return None

        # Extract path from tab-separated line
        parts = selected.split("\t")
        if len(parts) >= 2:
            return parts[1]
        return selected

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        print("Error: fzf not found or timed out", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Launch opencode in an opskit project")
    parser.add_argument("project", nargs="?", help="Project name or path (optional)")

    args = parser.parse_args()

    # Cache-first: rescan only when the cache is missing or stale.
    ensure_cache()
    projects = read_discovery_projects()
    if not projects:
        print("No projects cached. Run: opskit projects rescan")
        sys.exit(1)

    # Sort by last-used
    projects = sort_projects_by_last_used(projects)

    if args.project:
        # Try exact match first
        exact_match = None
        for proj in projects:
            proj_name = proj.get("name", "")
            proj_path = proj.get("path", "")
            if proj_name == args.project or proj_path == args.project or proj_path.endswith(args.project):
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
                print("Suggestions:", file=sys.stderr)
                for proj in projects[:5]:
                    print(f"  {proj.get('name', 'unknown')}", file=sys.stderr)
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
