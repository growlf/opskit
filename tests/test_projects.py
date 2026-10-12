"""Tests for opskit project discovery and cache management."""

import json
import subprocess
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from opskit._cache import (
    write_discovery_cache,
    read_discovery_projects,
    CACHE_DIR,
    LAST_DISCOVERY_FILE,
)


@pytest.fixture
def cache_setup(tmp_path, monkeypatch):
    """Set up a temporary cache directory and projects directory."""
    test_cache = tmp_path / ".opskit"
    test_cache.mkdir()
    monkeypatch.setattr("opskit._cache.CACHE_DIR", test_cache)
    monkeypatch.setattr("opskit._cache.LAST_DISCOVERY_FILE", test_cache / "last-discovery.json")
    monkeypatch.setattr("opskit._cache.LAST_USED_FILE", test_cache / "last-used.json")

    # Create a test projects directory with some fake projects
    projects_dir = tmp_path / "Projects"
    projects_dir.mkdir()

    # Create a project with .git and pack.yml
    proj1 = projects_dir / "test-project"
    proj1.mkdir()
    (proj1 / ".git").mkdir()
    (proj1 / ".opskit").mkdir()
    (proj1 / ".opskit" / "pack.yml").write_text(
        "name: test-project\ndescription: Test project\ndata_classification: public\n"
    )

    # Create a project with only .git
    proj2 = projects_dir / "git-only-project"
    proj2.mkdir()
    (proj2 / ".git").mkdir()

    # Create a project to skip (no .git, no pack.yml)
    proj3 = projects_dir / "not-a-project"
    proj3.mkdir()

    return test_cache, projects_dir


class TestScanProjectDir:
    """Test project directory scanning."""

    def test_scans_projects(self, cache_setup):
        cache_dir, projects_dir = cache_setup
        from bin.opskit_projects import scan_project_dir
        projects = scan_project_dir(str(projects_dir))

        # Should find test-project and git-only-project, but not not-a-project
        names = [p["name"] for p in projects]
        assert "test-project" in names
        assert "git-only-project" in names
        assert "not-a-project" not in names

    def test_project_has_required_fields(self, cache_setup):
        cache_dir, projects_dir = cache_setup
        from bin.opskit_projects import scan_project_dir
        projects = scan_project_dir(str(projects_dir))
        assert len(projects) > 0

        proj = projects[0]
        assert "name" in proj
        assert "path" in proj
        assert "description" in proj
        assert "classification" in proj
        assert "has_resume" in proj
        assert "git_branch" in proj
        assert "git_status" in proj

    def test_nonexistent_dir_returns_empty(self, cache_setup):
        cache_dir, _ = cache_setup
        from bin.opskit_projects import scan_project_dir
        projects = scan_project_dir("/nonexistent/path")
        assert projects == []


class TestDiscoveryCacheIntegration:
    """Test write/read of discovery cache."""

    def test_write_and_read_projects(self, cache_setup):
        cache_dir, projects_dir = cache_setup
        from bin.opskit_projects import scan_project_dir
        projects = scan_project_dir(str(projects_dir))

        now = "2026-01-01T00:00:00"
        data = {
            "version": 1,
            "timestamp": now,
            "projects_dir": str(projects_dir),
            "projects": projects,
        }
        write_discovery_cache(data)

        cached = read_discovery_projects()
        assert len(cached) == len(projects)

    def test_cache_stale_detection(self, cache_setup, monkeypatch):
        cache_dir, _ = cache_setup
        # Cache doesn't exist yet — should be stale
        from opskit._cache import cache_is_stale
        assert cache_is_stale(str(cache_dir)) is True
