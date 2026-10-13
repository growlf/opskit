#!/usr/bin/env python3
"""
opskit-projects.py — Project cache management.

Subcommands:
  rescan          Force full rescan of the configured projects_dir
  add <path>      Add a single project to the cache without rescanning
  list            Show cached projects
  config          Show or set the projects_dir path

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

def scan_project_dir(projects_dir: str):
    """Scan a directory for OpsKit-enabled projects.

    Returns a list of project dicts with name, path, description, classification,
    has_resume, git_branch, git_status.
    """
    projects_dir_path = Path(projects_dir).resolve()
    if not projects_dir_path.exists():
        print(f"Projects directory does not exist: {projects_dir}", file=sys.stderr)
        return []

    projects = []
    for entry in sorted(projects_dir_path.iterdir()):
        # Skip dotdirs and non-directories
        if entry.name.startswith("."):
            continue
        if not entry.is_dir():
            continue

        # Must contain .git/ or pack.yml to be considered a project
        git_dir = entry / ".git"
        pack_file = entry / ".opskit" / "pack.yml"

        if not git_dir.exists() and not pack_file.exists():
            continue

        project = _analyze_project(entry, git_dir, pack_file)
        if project:
            projects.append(project)

    return projects


def _analyze_project(entry: Path, git_dir: Path, pack_file: Path):
    """Analyze a single project directory.

    Returns a project dict or None if the project should be skipped.
    """
    # Get name from pack.yml or use directory name
    description = ""
    classification = "public"

    if pack_file.exists():
        try:
            with open(pack_file, "r") as f:
                pack_data = yaml.safe_load(f) or {}
            name = pack_data.get("name", entry.name)
            description = pack_data.get("description", "")
            classification = pack_data.get("data_classification", "public")
        except Exception:
            name = entry.name
    else:
        name = entry.name

    # Get git info
    git_branch = ""
    git_status = ""
    if git_dir.exists():
        try:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(entry), capture_output=True, text=True, timeout=10,
            )
            git_branch = branch_result.stdout.strip() or "detached"

            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(entry), capture_output=True, text=True, timeout=10,
            )
            git_status = "dirty" if status_result.stdout.strip() else "clean"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            git_branch = "unknown"
            git_status = "unknown"

    # Check for RESUME.md
    has_resume = (entry / "RESUME.md").exists()

    canonical_path = str(entry.resolve())

    return {
        "name": name,
        "path": canonical_path,
        "description": description,
        "classification": classification,
        "has_resume": has_resume,
        "git_branch": git_branch,
        "git_status": git_status,
    }


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


# ── Subcommands ──────────────────────────────────────────────────────────────

def cmd_rescan(args):
    """Force full rescan of the configured projects_dir."""
    projects_dir = get_projects_dir()
    print(f"Scanning projects in: {projects_dir}")

    projects = scan_project_dir(projects_dir)
    write_discovery_cache(_build_cache(projects_dir, projects))

    print(f"Found {len(projects)} project(s)")
    for proj in projects:
        status = "[resume]" if proj.get("has_resume") else ""
        print(f"  {proj['name']:30s} {proj.get('git_branch', ''):15s} {status}")


def cmd_add(args):
    """Add a single project to the cache."""
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    projects_dir = get_projects_dir()
    if not project_path.is_relative_to(Path(projects_dir).resolve()):
        print(f"Warning: path is outside projects_dir ({projects_dir})", file=sys.stderr)

    # Scan the single project
    pack_file = project_path / ".opskit" / "pack.yml"
    git_dir = project_path / ".git"

    projects = scan_project_dir(str(projects_dir))
    existing_paths = {p["path"] for p in projects}

    # Add the new project if not already present
    # Re-analyze it
    new_proj = _analyze_project(project_path, git_dir, pack_file)
    if new_proj and new_proj["path"] not in existing_paths:
        projects.append(new_proj)
        write_discovery_cache(_build_cache(projects_dir, projects))
        print(f"Added: {new_proj['name']} ({new_proj['path']})")
    elif new_proj:
        print(f"Already in cache: {new_proj['name']}")
    else:
        print(f"Could not analyze: {project_path}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """Show cached projects."""
    projects = read_discovery_cache()
    if projects is None:
        print("No cached projects. Run: opskit projects rescan")
        sys.exit(0)

    project_list = projects.get("projects", [])
    projects_dir = projects.get("projects_dir", "unknown")
    timestamp = projects.get("timestamp", "unknown")

    print(f"Projects dir: {projects_dir}")
    print(f"Cache updated: {timestamp}")
    print(f"Projects: {len(project_list)}")
    print()

    for proj in project_list:
        status = ""
        if proj.get("has_resume"):
            status = "[resume]"
        git_info = proj.get("git_branch", "?")
        if proj.get("git_status") == "dirty":
            git_info += " *"
        print(f"  {proj['name']:30s} {git_info:15s} {proj.get('git_status', ''):8s} {status}")


def cmd_config(args):
    """Show or set the projects_dir path."""
    config = read_config()

    if args.action == "show":
        print(f"projects_dir: {config.get('projects_dir', 'not set')}")
    elif args.action == "set":
        new_path = Path(args.path).resolve()
        new_path.mkdir(parents=True, exist_ok=True)
        config["projects_dir"] = str(new_path)
        write_config(config)
        print(f"Set projects_dir to: {new_path}")
    else:
        print(f"projects_dir: {config.get('projects_dir', 'not set')}")


def main():
    parser = argparse.ArgumentParser(description="Manage opskit project cache")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("rescan", help="Force full rescan of projects dir")
    sub.add_parser("list", help="Show cached projects")

    add_parser = sub.add_parser("add", help="Add a single project to cache")
    add_parser.add_argument("path", help="Path to project directory")

    config_parser = sub.add_parser("config", help="Show or set projects_dir")
    config_parser.add_argument("action", nargs="?", choices=["show", "set"], default="show")
    config_parser.add_argument("path", nargs="?", help="New projects_dir path (for 'set')")

    args = parser.parse_args()

    if args.command == "rescan":
        cmd_rescan(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
