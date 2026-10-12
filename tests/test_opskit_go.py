"""Tests for opskit-go.py — TUI launcher."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

# Reuse the matching tests from test_tui_matching.py
from test_tui_matching import TestFuzzyMatch

class TestGoFuzzyMatch(TestFuzzyMatch):
    """Test fuzzy matching from opskit-go.py."""
    pass
