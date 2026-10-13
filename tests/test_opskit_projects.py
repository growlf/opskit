"""Tests for opskit-projects.py — project cache management."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestOpskitProjects:
    """Test opskit-projects.py script."""

    def test_script_help(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "bin" / "opskit-projects.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "rescan" in result.stdout

    def test_script_exists(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-projects.py"
        assert script.exists()

    def test_script_compiles(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-projects.py"
        content = script.read_text()
        compile(content, str(script), "exec")
