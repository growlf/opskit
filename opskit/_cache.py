#!/usr/bin/env python3
"""
_cache.py — Shared cache module for opskit go/web/project commands.

Provides atomic read/write operations for the ~/.opskit/ cache files:
  - last-discovery.json  (project discovery cache)
  - last-used.json       (per-project usage tracking)

All file I/O uses tempfile + rename pattern for atomicity and concurrent-write
safety. All scripts (go.py, projects.py, etc.) import from this module.
"""

import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

CACHE_DIR = Path.home() / ".opskit"
CACHE_DIR_MODE = 0o700
FILE_MODE = 0o600
LAST_DISCOVERY_FILE = CACHE_DIR / "last-discovery.json"
LAST_USED_FILE = CACHE_DIR / "last-used.json"
CONFIG_FILE = CACHE_DIR / "config.yml"
DEFAULT_PROJECTS_DIR = Path.home() / "Projects"
MAX_LAST_USED_ENTRIES = 100
CACHE_STALE_HOURS = 24


# ── Config (single definition — go.py and projects.py both import these) ─────

def read_config() -> dict:
    """Read ~/.opskit/config.yml. Returns dict with defaults."""
    import yaml
    data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
    data.setdefault("projects_dir", str(DEFAULT_PROJECTS_DIR))
    return data


def write_config(data: dict):
    """Write ~/.opskit/config.yml atomically."""
    import yaml
    _atomic_write(CONFIG_FILE, yaml.dump(data, default_flow_style=False))


def get_projects_dir() -> str:
    """Get the configured projects_dir path."""
    return read_config().get("projects_dir", str(DEFAULT_PROJECTS_DIR))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_cache_dir():
    """Ensure ~/.opskit/ exists with correct permissions."""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(mode=CACHE_DIR_MODE, parents=True, exist_ok=True)
        os.chmod(str(CACHE_DIR), CACHE_DIR_MODE)


def _atomic_write(path: Path, data: str):
    """Write data to path atomically via tempfile + rename."""
    _ensure_cache_dir()
    dirpath = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dirpath), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.chmod(tmp_path, FILE_MODE)
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_json(path: Path):
    """Read and parse a JSON file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def _write_json(path: Path, data: dict):
    """Serialize and atomically write a dict as JSON."""
    _atomic_write(path, json.dumps(data, indent=2, default=str) + "\n")


# ── last-discovery.json operations ───────────────────────────────────────────

def read_discovery_cache():
    """Read the project discovery cache. Returns None if not found."""
    return _read_json(LAST_DISCOVERY_FILE)


def write_discovery_cache(data: dict):
    """Write the project discovery cache atomically."""
    _write_json(LAST_DISCOVERY_FILE, data)


def read_discovery_projects():
    """Read the cached project list. Returns empty list if not found."""
    cache = read_discovery_cache()
    if cache is None:
        return []
    return cache.get("projects", [])


def cache_is_stale(projects_dir: str) -> bool:
    """Check if the discovery cache is stale.

    Cache is stale if:
    - File doesn't exist or is unreadable
    - Older than CACHE_STALE_HOURS
    - projects_dir mtime differs from the value recorded at scan time
    """
    if not LAST_DISCOVERY_FILE.exists():
        return True

    cache = read_discovery_cache()
    if cache is None:
        return True

    cache_timestamp = cache.get("timestamp", "")
    try:
        cache_time = datetime.fromisoformat(cache_timestamp)
        if cache_time.tzinfo is None:
            cache_time = cache_time.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - cache_time).total_seconds() > CACHE_STALE_HOURS * 3600:
            return True
    except (ValueError, TypeError):
        return True

    # projects_dir mtime changed since the cache was written → new/removed entries.
    try:
        current_mtime = Path(projects_dir).resolve().stat().st_mtime
    except OSError:
        return True
    stored_mtime = cache.get("projects_dir_mtime")
    if stored_mtime is None or abs(current_mtime - float(stored_mtime)) > 1e-6:
        return True

    return False


def get_project_from_cache(path: str):
    """Look up a project by canonical path in the discovery cache."""
    projects = read_discovery_projects()
    for proj in projects:
        if proj.get("path") == path:
            return proj
    return None


# ── last-used.json operations ────────────────────────────────────────────────

def read_last_used():
    """Read the last-used cache. Returns default structure if not found."""
    data = _read_json(LAST_USED_FILE)
    if data is None:
        return {"version": 1, "entries": []}
    return data


def update_last_used(project_path: str):
    """Update the last-used timestamp for a project.

    - Moves existing entry to end of list (LRU)
    - Appends if new
    - Trims to MAX_LAST_USED_ENTRIES
    """
    _ensure_cache_dir()
    now = datetime.now(timezone.utc).isoformat()

    data = read_last_used()
    entries = data.get("entries", [])

    # Remove existing entry if present
    entries = [e for e in entries if e.get("project_path") != project_path]

    # Add new entry at end
    entries.append({
        "project_path": project_path,
        "timestamp": now,
    })

    # Trim to max entries
    if len(entries) > MAX_LAST_USED_ENTRIES:
        entries = entries[-MAX_LAST_USED_ENTRIES:]

    data["entries"] = entries
    _write_json(LAST_USED_FILE, data)


def get_last_used_order():
    """Get project paths sorted by last-used time (most recent first)."""
    data = read_last_used()
    entries = data.get("entries", [])
    # Sort by timestamp descending
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return [e["project_path"] for e in entries]


def get_sort_key(project_path: str):
    """Return a sort key for a project path based on last-used time.

    Most recent first. Projects not in the cache get a neutral key.
    """
    data = read_last_used()
    entries = data.get("entries", [])
    for entry in entries:
        if entry.get("project_path") == project_path:
            return entry.get("timestamp", "")
    return ""
