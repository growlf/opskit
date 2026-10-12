#!/usr/bin/env python3
"""
opskit-skills.py — Symlink management for agent skill directories.

Subcommands:
  setup       Create symlinks to opskit skills in agent skill dirs
  verify      Check all symlinks point to valid SKILL.md files
  cleanup     Remove opskit-managed symlinks

Creates symlinks in:
  - ~/.config/opencode/skills/ (flat, each skill as top-level symlink)
  - ~/.agents/skills/opskit/ (subdirectory, each skill as subdirectory symlink)

Source directory: ~/Projects/opskit/.opencode/skills/ (resolved from OPSKIT_ROOT
or git rev-parse).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()


def resolve_opskit_root():
    """Resolve the opskit root directory.

    Checks:
    1. OPSKIT_ROOT env var
    2. git rev-parse from script location
    3. ~/Projects/opskit as fallback
    """
    env_root = os.environ.get("OPSKIT_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root).resolve()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).resolve()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Fallback
    return Path.home() / "Projects" / "opskit"


OPSKIT_ROOT = resolve_opskit_root()
SKILLS_SOURCE = OPSKIT_ROOT / ".opencode" / "skills"
OPENCODE_SKILLS_DIR = Path.home() / ".config" / "opencode" / "skills"
AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills" / "opskit"


def _get_skills():
    """Get list of skill directory names from the source directory."""
    if not SKILLS_SOURCE.exists():
        print(f"Warning: skills source not found: {SKILLS_SOURCE}", file=sys.stderr)
        return []
    return sorted([d.name for d in SKILLS_SOURCE.iterdir() if d.is_dir()])


def _create_symlink(source: Path, target: Path, force: bool = False):
    """Create or verify a symlink. Returns status string."""
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            current_target = target.resolve()
            if current_target == source:
                return "unchanged"
            elif not force:
                print(f"  conflict: {target.name} -> {current_target} (use --force to overwrite)", file=sys.stderr)
                return "conflict"
        elif not force:
            print(f"  conflict: {target.name} is a file/directory (use --force to overwrite)", file=sys.stderr)
            return "conflict"

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        target.unlink()  # Remove existing symlink/file
    os.symlink(str(source), str(target))
    return "created"


def cmd_setup(args):
    """Create symlinks to opskit skills."""
    skills = _get_skills()
    if not skills:
        print("No skills found in source directory")
        return

    force = args.force
    created = 0
    unchanged = 0
    conflicts = 0

    print(f"Setting up skill symlinks from: {SKILLS_SOURCE}")
    print()

    # Opencode: flat symlinks in ~/.config/opencode/skills/
    opencode_target_dir = OPENCODE_SKILLS_DIR
    opencode_target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Opencode skills dir: {opencode_target_dir}")
    for skill_name in skills:
        source = SKILLS_SOURCE / skill_name
        target = opencode_target_dir / skill_name
        status = _create_symlink(source, target, force)
        if status == "created":
            created += 1
            print(f"  created: {skill_name}")
        elif status == "unchanged":
            unchanged += 1
            print(f"  unchanged: {skill_name}")
        elif status == "conflict":
            conflicts += 1
            print(f"  conflict: {skill_name}")

    print()

    # Agents: subdirectory symlinks in ~/.agents/skills/opskit/
    agents_target_dir = AGENTS_SKILLS_DIR
    agents_target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Agents skills dir: {agents_target_dir}")
    for skill_name in skills:
        source = SKILLS_SOURCE / skill_name
        target = agents_target_dir / skill_name
        status = _create_symlink(source, target, force)
        if status == "created":
            created += 1
            print(f"  created: {skill_name}")
        elif status == "unchanged":
            unchanged += 1
            print(f"  unchanged: {skill_name}")
        elif status == "conflict":
            conflicts += 1
            print(f"  conflict: {skill_name}")

    print()
    print(f"Summary: {created} created, {unchanged} unchanged, {conflicts} conflicts")

    if conflicts > 0 and not force:
        print("  Run with --force to overwrite conflicts")


def cmd_verify(args):
    """Check all symlinks point to valid SKILL.md files."""
    skills = _get_skills()
    if not skills:
        print("No skills found in source directory")
        return

    ok_count = 0
    fail_count = 0

    print(f"Verifying symlinks from: {SKILLS_SOURCE}")
    print()

    for skill_name in skills:
        # Check opencode symlink
        opencode_target = OPENCODE_SKILLS_DIR / skill_name
        agents_target = AGENTS_SKILLS_DIR / skill_name

        opencode_ok = opencode_target.is_symlink() and (opencode_target / "SKILL.md").exists()
        agents_ok = agents_target.is_symlink() and (agents_target / "SKILL.md").exists()

        status = "OK" if (opencode_ok and agents_ok) else "FAIL"
        if status == "OK":
            ok_count += 1
        else:
            fail_count += 1
            reasons = []
            if not opencode_ok:
                reasons.append(f"opencode: {opencode_target} missing or invalid")
            if not agents_ok:
                reasons.append(f"agents: {agents_target} missing or invalid")

        print(f"  {skill_name:30s} {status}" + (f"  {'; '.join(reasons)}" if status == "FAIL" else ""))

    print()
    print(f"Summary: {ok_count} OK, {fail_count} FAIL")


def cmd_cleanup(args):
    """Remove opskit-managed symlinks."""
    skills = _get_skills()
    if not skills:
        print("No skills found in source directory")
        return

    removed = 0

    print(f"Removing opskit symlinks...")
    print()

    for skill_name in skills:
        # Remove opencode symlink
        opencode_target = OPENCODE_SKILLS_DIR / skill_name
        if opencode_target.is_symlink():
            opencode_target.unlink()
            print(f"  removed: {skill_name} (opencode)")
            removed += 1

        # Remove agents symlink
        agents_target = AGENTS_SKILLS_DIR / skill_name
        if agents_target.is_symlink():
            agents_target.unlink()
            print(f"  removed: {skill_name} (agents)")
            removed += 1

    print()
    print(f"Removed {removed} symlink(s)")


def main():
    parser = argparse.ArgumentParser(description="Manage opskit skill symlinks")
    sub = parser.add_subparsers(dest="command")

    setup_parser = sub.add_parser("setup", help="Create skill symlinks")
    setup_parser.add_argument("--force", action="store_true", help="Overwrite conflicts")

    sub.add_parser("verify", help="Verify skill symlinks")
    sub.add_parser("cleanup", help="Remove skill symlinks")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
