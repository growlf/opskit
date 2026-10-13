"""Tests for opskit-skills.py — symlink management."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from test_skills import TestOpskitSkills

class TestSkills(TestOpskitSkills):
    """Test opskit-skills.py."""
    pass
