"""Tests for bin/opskit-go.py — TUI launcher."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# Reuse the matching tests, which load the real opskit-go.py as a module.
from test_tui_matching import TestFuzzyMatch, _go


class TestGoFuzzyMatch(TestFuzzyMatch):
    """Test fuzzy matching from the shipped opskit-go.py."""


class TestSortByLastUsed:
    def test_last_used_projects_come_first(self, monkeypatch):
        projects = [
            {"name": "A", "path": "/p/a"},
            {"name": "B", "path": "/p/b"},
        ]
        monkeypatch.setattr(_go, "get_last_used_order", lambda: ["/p/b"])
        ordered = _go.sort_projects_by_last_used(projects)
        assert ordered[0]["path"] == "/p/b"
        assert {p["path"] for p in ordered} == {"/p/a", "/p/b"}

    def test_uncached_projects_are_kept(self, monkeypatch):
        projects = [{"name": "A", "path": "/p/a"}]
        monkeypatch.setattr(_go, "get_last_used_order", lambda: [])
        ordered = _go.sort_projects_by_last_used(projects)
        assert ordered == projects
