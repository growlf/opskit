"""Tests for opskit-skills.py — symlink management."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestOpskitSkills:
    """Test opskit-skills.py script."""

    def test_script_help(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "bin" / "opskit-skills.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "setup" in result.stdout

    def test_script_exists(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-skills.py"
        assert script.exists()

    def test_script_compiles(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-skills.py"
        content = script.read_text()
        compile(content, str(script), "exec")
