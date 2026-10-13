#!/usr/bin/env python3
"""
opskit-projects.py — Project cache management.

Subcommands:
  rescan          Force full rescan of the configured projects_dir
  bootstrap       Enable every OpsKit member (.opskit/pack.yml) found under projects_dir
  add <path>      Enable a project and refresh the cache
  remove <name>   Disable a project (drop it from the enabled list)
  list            Show cached (enabled) projects
  config          Show or set the projects_dir path

The set of projects offered by `opskit go`/`web` is the `projects:` allow-list in
~/.opskit/config.yml. When that list is empty, discovery falls back to every
candidate found under projects_dir (so `rescan` still reports what exists).

Reads/writes ~/.opskit/last-discovery.json and ~/.opskit/config.yml.
Uses opskit._cache for atomic cache operations.
"""

import argparse
import subprocess
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Add opskit directory to path for _cache import
_SCRIPT_DIR = Path(__file__).parent.resolve()
_OPSKIT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_OPSKIT_ROOT))

from opskit._cache import (
    read_discovery_cache,
    write_discovery_cache,
    read_config,
    write_config,
    get_projects_dir,
)


# ── Scan helpers ─────────────────────────────────────────────────────────────

# Directories never worth descending into (VCS internals, caches, build output).
PRUNE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "target",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", ".next",
    "coverage", "htmlcov", ".idea", ".vscode",
}
MAX_DEPTH = 4


def _is_worktree(entry: Path) -> bool:
    """A linked git worktree (.git is a file) or a *-wt-* scratch directory."""
    if (entry / ".git").is_file():
        return True
    return "-wt-" in entry.name


def discover_projects(projects_dir: str, members_only: bool = False):
    """Recursively discover projects under projects_dir.

    A directory is a project if it contains .git/ or .opskit/pack.yml. Grouping
    directories (neither) are descended into, bounded by MAX_DEPTH. Git worktrees
    are skipped by default. When members_only is set, only OpsKit members
    (.opskit/pack.yml) are returned.
    """
    root = Path(projects_dir).resolve()
    if not root.exists():
        print(f"Projects directory does not exist: {projects_dir}", file=sys.stderr)
        return []

    projects = []

    def walk(directory: Path, depth: int):
        if depth > MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in PRUNE_DIRS:
                continue
            if not entry.is_dir() or entry.is_symlink():
                continue

            git_dir = entry / ".git"
            pack_file = entry / ".opskit" / "pack.yml"
            has_git = git_dir.exists()
            has_pack = pack_file.exists()

            if has_git or has_pack:
                if _is_worktree(entry):
                    continue
                if members_only and not has_pack:
                    continue
                project = _analyze_project(entry, pack_file, root)
                if project:
                    projects.append(project)
                # Do not descend into a matched project.
            else:
                walk(entry, depth + 1)

    walk(root, 1)
    return projects


def scan_project_dir(projects_dir: str):
    """Backwards-compatible full discovery (all candidates)."""
    return discover_projects(projects_dir)


def _analyze_project(entry: Path, pack_file: Path, root: Path):
    """Build a project record. No git calls here — that is done lazily."""
    description = ""
    classification = "public"
    name = entry.name

    if pack_file.exists():
        try:
            with open(pack_file, "r") as f:
                pack_data = yaml.safe_load(f) or {}
            name = pack_data.get("name", entry.name)
            description = pack_data.get("description", "")
            classification = pack_data.get("data_classification", "public")
        except Exception:
            name = entry.name

    try:
        rel = entry.relative_to(root).as_posix()
    except ValueError:
        rel = entry.name

    return {
        "name": name,
        "path": str(entry.resolve()),
        "rel": rel,
        "description": description,
        "classification": classification,
        "has_resume": (entry / "RESUME.md").exists(),
    }


def git_info(path: str):
    """Return (branch, status) for a project, computed on demand."""
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


# ── Enabled-list matching ────────────────────────────────────────────────────

def _selector_key(value: str) -> str:
    return value.strip().rstrip("/").lower().lstrip("./")


def project_matches_selector(proj: dict, selector: str) -> bool:
    """True if a selector (rel path, basename, name, or abs path) names proj."""
    s = _selector_key(selector)
    if not s:
        return False
    candidates = {
        _selector_key(proj.get("rel", "")),
        Path(proj.get("path", "")).name.lower(),
        proj.get("name", "").lower(),
        proj.get("path", "").lower(),
    }
    return s in candidates


def filter_enabled(projects, selectors):
    """Return (kept, unmatched) for the configured selectors."""
    kept, unmatched = [], []
    for sel in selectors:
        matched = [p for p in projects if project_matches_selector(p, sel)]
        if not matched:
            unmatched.append(sel)
        for m in matched:
            if m not in kept:
                kept.append(m)
    return kept, unmatched


def _projects_dir_mtime(projects_dir: str):
    """mtime of projects_dir (float), or None if it can't be stat'd."""
    try:
        return Path(projects_dir).resolve().stat().st_mtime
    except OSError:
        return None


def _build_cache(projects_dir: str, projects: list) -> dict:
    return {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "projects_dir": projects_dir,
        "projects_dir_mtime": _projects_dir_mtime(projects_dir),
        "projects": projects,
    }


def _run_rescan(projects_dir: str):
    """Discover, apply the enabled filter, write the cache. Returns the list."""
    candidates = discover_projects(projects_dir)
    selectors = read_config().get("projects") or []
    if selectors:
        projects, unmatched = filter_enabled(candidates, selectors)
        for sel in unmatched:
            print(f"Warning: configured project not found: {sel}", file=sys.stderr)
    else:
        projects = candidates
    write_discovery_cache(_build_cache(projects_dir, projects))
    return projects


# ── Subcommands ──────────────────────────────────────────────────────────────

def cmd_rescan(args):
    """Force full rescan of the configured projects_dir."""
    projects_dir = get_projects_dir()
    print(f"Scanning projects in: {projects_dir}")
    projects = _run_rescan(projects_dir)
    print(f"Found {len(projects)} project(s)")
    for proj in projects:
        status = "[resume]" if proj.get("has_resume") else ""
        print(f"  {proj['rel']:30s} {status}")


def cmd_bootstrap(args):
    """Enable every OpsKit member (.opskit/pack.yml) found under projects_dir."""
    projects_dir = get_projects_dir()
    members = discover_projects(projects_dir, members_only=True)

    config = read_config()
    selectors = list(config.get("projects") or [])
    for proj in members:
        if proj["rel"] not in selectors:
            selectors.append(proj["rel"])
    config["projects"] = selectors
    write_config(config)

    if members:
        print(f"Enabled {len(members)} OpsKit project(s):")
        for proj in members:
            print(f"  {proj['rel']}")
    else:
        print("No OpsKit projects (.opskit/pack.yml) found.")

    projects = _run_rescan(projects_dir)
    print(f"Found {len(projects)} project(s)")


def cmd_add(args):
    """Enable a single project and refresh the cache."""
    projects_dir = get_projects_dir()
    projects_root = Path(projects_dir).resolve()

    candidate = Path(args.path)
    if not candidate.is_absolute():
        candidate = projects_root / args.path
    project_path = candidate.resolve()

    if not project_path.exists():
        matches = [
            p for p in discover_projects(projects_dir)
            if p["name"].lower() == args.path.lower()
            or Path(p["path"]).name.lower() == args.path.lower()
        ]
        if len(matches) == 1:
            project_path = Path(matches[0]["path"])
        else:
            print(f"Path not found: {args.path}", file=sys.stderr)
            sys.exit(1)

    has_git = (project_path / ".git").exists()
    has_pack = (project_path / ".opskit" / "pack.yml").exists()
    if not has_git and not has_pack:
        print(
            f"Not an OpsKit project (no .git/ or .opskit/pack.yml): {project_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    if project_path.is_relative_to(projects_root):
        selector = project_path.relative_to(projects_root).as_posix()
    else:
        print(f"Warning: path is outside projects_dir ({projects_dir})", file=sys.stderr)
        selector = str(project_path)

    config = read_config()
    selectors = list(config.get("projects") or [])
    if selector in selectors:
        print(f"Already enabled: {selector}")
    else:
        selectors.append(selector)
        config["projects"] = selectors
        write_config(config)
        print(f"Enabled: {selector}")

    projects = _run_rescan(projects_dir)
    print(f"Found {len(projects)} project(s)")


def cmd_remove(args):
    """Disable a project by dropping its selector from the enabled list."""
    projects_dir = get_projects_dir()
    config = read_config()
    selectors = list(config.get("projects") or [])
    target = _selector_key(args.name)
    kept = [s for s in selectors if _selector_key(s) != target]
    if len(kept) == len(selectors):
        print(f"Not enabled: {args.name}", file=sys.stderr)
        sys.exit(1)
    config["projects"] = kept
    write_config(config)
    print(f"Disabled: {args.name}")

    projects = _run_rescan(projects_dir)
    print(f"Found {len(projects)} project(s)")


def cmd_list(args):
    """Show cached (enabled) projects."""
    cache = read_discovery_cache()
    if cache is None:
        print("No cached projects. Run: opskit projects rescan")
        sys.exit(0)

    project_list = cache.get("projects", [])
    projects_dir = cache.get("projects_dir", "unknown")
    timestamp = cache.get("timestamp", "unknown")

    print(f"Projects dir: {projects_dir}")
    print(f"Cache updated: {timestamp}")
    print(f"Projects: {len(project_list)}")
    print()

    for proj in project_list:
        branch, status = ("-", "-")
        if (Path(proj["path"]) / ".git").exists():
            branch, status = git_info(proj["path"])
        resume = "[resume]" if proj.get("has_resume") else ""
        dirty = " *" if status == "dirty" else ""
        print(f"  {proj.get('rel', proj['name']):30s} {branch:15s}{dirty:2s} {resume}")


def cmd_config(args):
    """Show or set the projects_dir path (and the enabled list)."""
    config = read_config()

    if args.action == "set":
        if not args.path:
            print("config set requires a path", file=sys.stderr)
            sys.exit(1)
        new_path = Path(args.path).resolve()
        new_path.mkdir(parents=True, exist_ok=True)
        config["projects_dir"] = str(new_path)
        write_config(config)
        print(f"Set projects_dir to: {new_path}")
    else:
        print(f"projects_dir: {config.get('projects_dir', 'not set')}")
        selectors = config.get("projects") or []
        print(f"projects: {len(selectors)} enabled")
        for sel in selectors:
            print(f"  - {sel}")


def main():
    parser = argparse.ArgumentParser(description="Manage opskit project cache")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("rescan", help="Force full rescan of projects dir")
    sub.add_parser("bootstrap", help="Enable every OpsKit member found under projects_dir")
    sub.add_parser("list", help="Show cached projects")

    add_parser = sub.add_parser("add", help="Enable a project and refresh the cache")
    add_parser.add_argument("path", help="Path (or name) of the project directory")

    remove_parser = sub.add_parser("remove", help="Disable a project")
    remove_parser.add_argument("name", help="Project selector (rel path, basename, or name)")

    config_parser = sub.add_parser("config", help="Show or set projects_dir")
    config_parser.add_argument("action", nargs="?", choices=["show", "set"], default="show")
    config_parser.add_argument("path", nargs="?", help="New projects_dir path (for 'set')")

    args = parser.parse_args()

    if args.command == "rescan":
        cmd_rescan(args)
    elif args.command == "bootstrap":
        cmd_bootstrap(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
