"""Tests for bin/opskit-go.py — TUI matching logic.

Loads the real script as a module so tests exercise the shipped
implementation rather than a copy (a copy drifted silently before).
"""

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


def _load_go_module():
    spec = importlib.util.spec_from_file_location(
        "opskit_go", _ROOT / "bin" / "opskit-go.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_go = _load_go_module()
fuzzy_match_projects = _go.fuzzy_match_projects


class TestFuzzyMatch:
    """Test fuzzy matching logic (the shipped function)."""

    def test_exact_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "Widget", "path": "/home/user/Projects/Widget"},
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
            {"name": "Widget", "path": "/home/user/Projects/Widget"},
        ]
        matches = fuzzy_match_projects("phoe", projects)
        assert len(matches) == 1
        assert matches[0]["name"] == "Phoenix"

    def test_no_match(self):
        projects = [
            {"name": "Phoenix", "path": "/home/user/Projects/Phoenix"},
            {"name": "Widget", "path": "/home/user/Projects/Widget"},
        ]
        matches = fuzzy_match_projects("nonexistent", projects)
        assert len(matches) == 0

    def test_path_match(self):
        projects = [{"name": "Other", "path": "/home/user/Projects/Phoenix"}]
        matches = fuzzy_match_projects("Phoenix", projects)
        assert len(matches) == 1

    def test_case_insensitive(self):
        projects = [{"name": "Phoenix", "path": "/home/user/Projects/Phoenix"}]
        matches = fuzzy_match_projects("PHOENIX", projects)
        assert len(matches) == 1

    def test_empty_projects_list(self):
        matches = fuzzy_match_projects("anything", [])
        assert len(matches) == 0
