"""Tests for opskit-projects.py — project cache management."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from test_projects import TestDiscoveryCache

class TestProjectsCache(TestDiscoveryCache):
    """Test project cache."""
    pass
