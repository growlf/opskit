"""Tests for opskit-secrets.py — secrets engine router."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestOpskitSecrets:
    """Test opskit-secrets.py script."""

    def test_script_help(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "bin" / "opskit-secrets.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "secret_name" in result.stdout

    def test_script_exists(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-secrets.py"
        assert script.exists()

    def test_script_compiles(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-secrets.py"
        content = script.read_text()
        compile(content, str(script), "exec")
