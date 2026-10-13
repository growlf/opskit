"""Tests for opskit-go.py — TUI matching logic."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from opskit._cache import CACHE_DIR, read_discovery_projects


def fuzzy_match_projects(name, projects):
    """Fuzzy match a project name against the project list.

    Copied from opskit-go.py for testing.
    """
    name_lower = name.lower()
    matches = []
    for proj in projects:
        proj_name = proj.get("name", "").lower()
        proj_path = proj.get("path", "").lower()
        if name_lower in proj_name or name_lower in proj_path:
            matches.append(proj)
    return matches


class TestFuzzyMatch:
    """Test fuzzy matching logic."""

    def test_exact_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "BMS", "path": "/home/user/Projects/BMS"},
        ]
        matches = fuzzy_match_projects("Phoenix", projects)
        assert len(matches) == 1
        assert matches[0]["name"] == "Phoenix"

    def test_partial_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "Phoenix-web", "path": "/home/user/Projects/Phoenix-web"},
        ]
        matches = fuzzy_match_projects("phoenix", projects)
        assert len(matches) == 2

    def test_single_fuzzy_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "BMS", "path": "/home/user/Projects/BMS"},
        ]
        matches = fuzzy_match_projects("phoe", projects)
        assert len(matches) == 1
        assert matches[0]["name"] == "Phoenix"

    def test_no_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "BMS", "path": "/home/user/Projects/BMS"},
        ]
        matches = fuzzy_match_projects("nonexistent", projects)
        assert len(matches) == 0

    def test_path_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
        ]
        matches = fuzzy_match_projects("Phoenix", projects)
        assert len(matches) == 1

    def test_case_insensitive(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
        ]
        matches = fuzzy_match_projects("PHOENIX", projects)
        assert len(matches) == 1

    def test_empty_projects_list(self):
        matches = fuzzy_match_projects("anything", [])
        assert len(matches) == 0
