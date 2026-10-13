"""Tests for bin/opskit-projects.py — project cache management.

Runs the real script under a sandboxed HOME so ~/.opskit/ is a temp dir.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "bin" / "opskit-projects.py"


@pytest.fixture
def sandbox(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    projects = tmp_path / "projects"
    (projects / "Demo" / ".git").mkdir(parents=True)
    env = dict(os.environ)
    env["HOME"] = str(home)
    return {"home": home, "projects": projects, "env": env}


def _run(args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30, env=env,
    )


class TestOpskitProjects:
    def test_help_lists_rescan(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "rescan" in result.stdout

    def test_script_compiles(self):
        compile(SCRIPT.read_text(), str(SCRIPT), "exec")

    def test_config_set_then_show(self, sandbox):
        result = _run(["config", "set", str(sandbox["projects"])], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert str(sandbox["projects"].resolve()) in result.stdout

        shown = _run(["config", "show"], sandbox["env"])
        assert str(sandbox["projects"].resolve()) in shown.stdout

    def test_rescan_writes_cache_and_finds_project(self, sandbox):
        _run(["config", "set", str(sandbox["projects"])], sandbox["env"])
        result = _run(["rescan"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert "Found 1 project" in result.stdout

        cache_file = sandbox["home"] / ".opskit" / "last-discovery.json"
        data = json.loads(cache_file.read_text())
        assert data["projects"][0]["name"] == "Demo"
        assert "projects_dir_mtime" in data

    def test_list_shows_cached_project(self, sandbox):
        _run(["config", "set", str(sandbox["projects"])], sandbox["env"])
        _run(["rescan"], sandbox["env"])
        result = _run(["list"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert "Demo" in result.stdout

    def test_list_without_cache_is_graceful(self, sandbox):
        result = _run(["list"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert "No cached projects" in result.stdout
