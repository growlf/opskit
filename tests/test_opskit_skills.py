"""Tests for bin/opskit-skills.py — symlink management.

Runs the real script in a sandboxed HOME + OPSKIT_ROOT so no live
user config is touched. Regression cover for cleanup safety: a
user-created symlink that merely shares a skill's name must survive.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "bin" / "opskit-skills.py"


@pytest.fixture
def sandbox(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    repo = tmp_path / "repo"
    skill = repo / ".opencode" / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n")
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["OPSKIT_ROOT"] = str(repo)
    return {"home": home, "repo": repo, "env": env, "skill": skill}


def _run(args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30, env=env,
    )


class TestSkillsSymlinks:
    def test_help_lists_subcommands(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "setup" in result.stdout

    def test_script_compiles(self):
        compile(SCRIPT.read_text(), str(SCRIPT), "exec")

    def test_setup_creates_symlinks_in_both_dirs(self, sandbox):
        result = _run(["setup"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert (sandbox["home"] / ".config" / "opencode" / "skills" / "demo").is_symlink()
        assert (sandbox["home"] / ".agents" / "skills" / "opskit" / "demo").is_symlink()

    def test_cleanup_removes_opskit_symlink(self, sandbox):
        _run(["setup"], sandbox["env"])
        result = _run(["cleanup"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert not (sandbox["home"] / ".config" / "opencode" / "skills" / "demo").exists()
        assert not (sandbox["home"] / ".agents" / "skills" / "opskit" / "demo").exists()

    def test_cleanup_preserves_foreign_symlink(self, sandbox):
        # A user-created symlink that happens to share the skill's name.
        foreign = sandbox["home"] / ".config" / "opencode" / "skills" / "demo"
        foreign.parent.mkdir(parents=True)
        foreign_target = sandbox["home"] / "my-own-skill"
        foreign_target.mkdir()
        os.symlink(str(foreign_target), str(foreign))

        # A genuine opskit-managed link alongside it.
        managed = sandbox["home"] / ".agents" / "skills" / "opskit" / "demo"
        managed.parent.mkdir(parents=True)
        os.symlink(str(sandbox["skill"]), str(managed))

        result = _run(["cleanup"], sandbox["env"])
        assert result.returncode == 0, result.stderr
        assert foreign.is_symlink(), "foreign symlink must be preserved"
        assert not managed.exists(), "opskit-managed symlink must be removed"
        assert "skipped" in result.stdout
