"""Tests for opskit-skills.py — symlink management."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

# Reuse the skills tests
from test_skills import TestGetSkills, TestSymlinkCreation

class TestSkillsGet(TestGetSkills):
    """Test skill discovery."""
    pass

class TestSkillsSymlink(TestSymlinkCreation):
    """Test symlink creation."""
    pass
