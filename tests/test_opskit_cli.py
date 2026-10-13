"""Tests for the bin/opskit dispatcher.

The go/web/skills/projects commands must forward their argv verbatim to the
owning bin/opskit-*.py sub-script — including `--help`, which must reach the
sub-script rather than being answered by a dispatcher stub.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "bin" / "opskit"


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    e = dict(os.environ)
    e["HOME"] = str(home)
    return e


def _run(args, environment):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30, env=environment,
    )


@pytest.mark.parametrize("cmd", ["go", "skills", "projects"])
def test_help_is_forwarded_to_subscript(cmd, env):
    result = _run([cmd, "--help"], env)
    assert result.returncode == 0, result.stderr
    assert f"opskit-{cmd}.py" in result.stdout


def test_top_level_help_lists_subcommands(env):
    result = _run(["--help"], env)
    assert result.returncode == 0
    for cmd in ("go", "web", "skills", "projects"):
        assert cmd in result.stdout


def test_projects_config_set_is_forwarded(env, tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    result = _run(["projects", "config", "set", str(target)], env)
    assert result.returncode == 0, result.stderr
    assert str(target.resolve()) in result.stdout
