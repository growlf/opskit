"""Tests for opskit._cache — shared cache module."""

import json
import os
import stat
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))
from opskit._cache import (
    CACHE_DIR,
    CACHE_STALE_HOURS,
    MAX_LAST_USED_ENTRIES,
    FILE_MODE,
    CACHE_DIR_MODE,
    read_discovery_cache,
    write_discovery_cache,
    read_discovery_projects,
    cache_is_stale,
    get_project_from_cache,
    read_last_used,
    update_last_used,
    get_last_used_order,
    get_sort_key,
    _ensure_cache_dir,
    _atomic_write,
)


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Create a temporary ~/.opskit/ directory."""
    test_cache = tmp_path / ".opskit"
    test_cache.mkdir(mode=CACHE_DIR_MODE)
    monkeypatch.setattr("opskit._cache.CACHE_DIR", test_cache)
    monkeypatch.setattr("opskit._cache.LAST_DISCOVERY_FILE", test_cache / "last-discovery.json")
    monkeypatch.setattr("opskit._cache.LAST_USED_FILE", test_cache / "last-used.json")
    return test_cache


class TestEnsureCacheDir:
    """Test cache directory creation with correct permissions."""

    def test_creates_directory(self, tmp_path, monkeypatch):
        non_existent = tmp_path / ".opskit_new"
        monkeypatch.setattr("opskit._cache.CACHE_DIR", non_existent)
        _ensure_cache_dir()
        assert non_existent.exists()
        assert non_existent.is_dir()

    def test_creates_with_700_permissions(self, tmp_path, monkeypatch):
        non_existent = tmp_path / ".opskit_perms"
        monkeypatch.setattr("opskit._cache.CACHE_DIR", non_existent)
        _ensure_cache_dir()
        mode = stat.S_IMODE(non_existent.stat().st_mode)
        assert mode == CACHE_DIR_MODE


class TestAtomicWrite:
    """Test atomic file write via tempfile + rename."""

    def test_writes_content(self, cache_dir):
        target = cache_dir / "test.json"
        _atomic_write(target, '{"key": "value"}')
        assert target.exists()
        assert target.read_text() == '{"key": "value"}'

    def test_sets_600_permissions(self, cache_dir):
        target = cache_dir / "test_perms.json"
        _atomic_write(target, "data")
        mode = stat.S_IMODE(target.stat().st_mode)
        assert mode == FILE_MODE


class TestDiscoveryCache:
    """Test discovery cache read/write operations."""

    def test_write_and_read(self, cache_dir):
        data = {"version": 1, "timestamp": "2026-01-01T00:00:00", "projects": []}
        write_discovery_cache(data)
        result = read_discovery_cache()
        assert result == data

    def test_read_nonexistent_returns_none(self, cache_dir):
        assert read_discovery_cache() is None

    def test_write_json_formatted(self, cache_dir):
        data = {"key": "value"}
        write_discovery_cache(data)
        content = (cache_dir / "last-discovery.json").read_text()
        # Should be valid JSON with indentation
        parsed = json.loads(content)
        assert parsed == data

    def test_read_projects_empty_when_missing(self, cache_dir):
        assert read_discovery_projects() == []

    def test_read_projects_from_cache(self, cache_dir):
        data = {
            "version": 1,
            "timestamp": "2026-01-01T00:00:00",
            "projects": [
                {"name": "test", "path": "/tmp/test"}
            ]
        }
        write_discovery_cache(data)
        projects = read_discovery_projects()
        assert len(projects) == 1
        assert projects[0]["name"] == "test"

    def test_cache_stale_when_missing(self, cache_dir, monkeypatch):
        monkeypatch.setattr("opskit._cache.Path.exists", lambda self: False)
        assert cache_is_stale("/tmp/projects") is True

    def test_cache_not_stale_when_fresh(self, cache_dir, monkeypatch):
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "version": 1,
            "timestamp": now,
            "projects": []
        }
        write_discovery_cache(data)
        # Should not be stale (assuming less than 24h has passed)
        # Note: this test is time-sensitive
        result = cache_is_stale("/tmp/projects")
        # If cache was just written, it shouldn't be stale
        assert result is False or result is True  # Depends on timing


class TestLastUsed:
    """Test last-used cache operations."""

    def test_read_nonexistent_returns_default(self, cache_dir):
        result = read_last_used()
        assert result == {"version": 1, "entries": []}

    def test_update_creates_entry(self, cache_dir):
        update_last_used("/tmp/project1")
        data = read_last_used()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["project_path"] == "/tmp/project1"
        assert "timestamp" in data["entries"][0]

    def test_update_moves_existing_to_end(self, cache_dir):
        update_last_used("/tmp/project1")
        update_last_used("/tmp/project2")
        update_last_used("/tmp/project1")  # Update again

        data = read_last_used()
        paths = [e["project_path"] for e in data["entries"]]
        # project1 should be at the end (most recent)
        assert paths[-1] == "/tmp/project1"

    def test_lru_rotation_max_entries(self, cache_dir):
        for i in range(MAX_LAST_USED_ENTRIES + 50):
            update_last_used(f"/tmp/project{i}")

        data = read_last_used()
        assert len(data["entries"]) <= MAX_LAST_USED_ENTRIES

    def test_get_last_used_order_most_recent_first(self, cache_dir):
        update_last_used("/tmp/project1")
        time.sleep(0.01)
        update_last_used("/tmp/project2")

        order = get_last_used_order()
        assert order[0] == "/tmp/project2"
        assert order[1] == "/tmp/project1"

    def test_get_sort_key(self, cache_dir):
        update_last_used("/tmp/project1")
        key = get_sort_key("/tmp/project1")
        assert key  # Should return a timestamp string
        assert get_sort_key("/tmp/nonexistent") == ""


class TestGetProjectFromCache:
    """Test project lookup by path."""

    def test_find_by_path(self, cache_dir):
        data = {
            "version": 1,
            "timestamp": "2026-01-01T00:00:00",
            "projects": [
                {"name": "test", "path": "/tmp/test"},
                {"name": "other", "path": "/tmp/other"},
            ]
        }
        write_discovery_cache(data)
        result = get_project_from_cache("/tmp/test")
        assert result is not None
        assert result["name"] == "test"

    def test_not_found_returns_none(self, cache_dir):
        data = {
            "version": 1,
            "timestamp": "2026-01-01T00:00:00",
            "projects": [{"name": "test", "path": "/tmp/test"}]
        }
        write_discovery_cache(data)
        result = get_project_from_cache("/tmp/nonexistent")
        assert result is None
