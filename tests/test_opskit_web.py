"""Tests for opskit-web.py — opencode web wrapper."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))


class TestOpskitWeb:
    """Test opskit-web.py script exists and has correct structure."""

    def test_script_exists(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-web.py"
        assert script.exists(), "opskit-web.py should exist"

    def test_script_is_executable_python(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-web.py"
        content = script.read_text()
        assert "#!/usr/bin/env python3" in content or "import os" in content

    def test_invokes_opencode_web(self):
        script = Path(__file__).parent.parent / "bin" / "opskit-web.py"
        content = script.read_text()
        assert "opencode" in content and "web" in content
