"""Tests for opskit-projects.py — project cache management."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

# Reuse the project discovery tests
from test_projects import TestScanProjectDir, TestDiscoveryCacheIntegration

class TestProjectsRescan(TestScanProjectDir):
    """Test project rescan."""
    pass

class TestProjectsCache(TestDiscoveryCacheIntegration):
    """Test project cache."""
    pass
