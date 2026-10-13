"""Tests for opskit project discovery and cache management."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from opskit._cache import (
    write_discovery_cache,
    read_discovery_projects,
)


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Set up a temporary cache directory."""
    test_cache = tmp_path / ".opskit"
    test_cache.mkdir()
    monkeypatch.setattr("opskit._cache.CACHE_DIR", test_cache)
    monkeypatch.setattr("opskit._cache.LAST_DISCOVERY_FILE", test_cache / "last-discovery.json")
    monkeypatch.setattr("opskit._cache.LAST_USED_FILE", test_cache / "last-used.json")
    return test_cache


class TestDiscoveryCache:
    """Test discovery cache read/write."""

    def test_write_and_read_projects(self, cache_dir):
        data = {
            "version": 1,
            "timestamp": "2026-01-01T00:00:00",
            "projects_dir": "/tmp/test",
            "projects": [{"name": "test", "path": "/tmp/test"}],
        }
        write_discovery_cache(data)
        cached = read_discovery_projects()
        assert len(cached) == 1
        assert cached[0]["name"] == "test"

    def test_cache_stale_when_missing(self, cache_dir):
        from opskit._cache import cache_is_stale
        assert cache_is_stale("/tmp/projects") is True
