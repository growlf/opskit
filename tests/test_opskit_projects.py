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


def _write_config(home, projects_dir, projects=None):
    d = home / ".opskit"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"projects_dir: {projects_dir}"]
    if projects is not None:
        lines.append("projects:")
        for p in projects:
            lines.append(f"  - {p}")
    (d / "config.yml").write_text("\n".join(lines) + "\n")


def _env(home):
    e = dict(os.environ)
    e["HOME"] = str(home)
    return e


def _cache(home):
    return json.loads((home / ".opskit" / "last-discovery.json").read_text())


def _cfg(home):
    import yaml
    return yaml.safe_load((home / ".opskit" / "config.yml").read_text()) or {}


@pytest.fixture
def tree(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    projects = tmp_path / "projects"
    projects.mkdir()
    return {"home": home, "projects": projects, "env": _env(home)}


class TestRecursiveDiscovery:
    def test_finds_nested_project_through_grouping_dir(self, tree):
        (tree["projects"] / "group" / "real" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"])
        result = _run(["rescan"], tree["env"])
        assert result.returncode == 0, result.stderr
        assert "Found 1 project" in result.stdout
        proj = _cache(tree["home"])["projects"][0]
        assert proj["name"] == "real"
        assert proj["rel"] == "group/real"

    def test_excludes_git_worktrees(self, tree):
        (tree["projects"] / "Foo" / ".git").mkdir(parents=True)
        wt = tree["projects"] / "Foo-wt-x"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: /somewhere\n")
        _write_config(tree["home"], tree["projects"])
        _run(["rescan"], tree["env"])
        names = [p["name"] for p in _cache(tree["home"])["projects"]]
        assert names == ["Foo"]

    def test_does_not_descend_into_a_project(self, tree):
        proj = tree["projects"] / "Outer"
        (proj / ".git").mkdir(parents=True)
        (proj / "inner" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"])
        _run(["rescan"], tree["env"])
        rels = [p["rel"] for p in _cache(tree["home"])["projects"]]
        assert rels == ["Outer"]

    def test_scan_records_no_git_fields(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"])
        _run(["rescan"], tree["env"])
        proj = _cache(tree["home"])["projects"][0]
        assert "git_branch" not in proj
        assert "git_status" not in proj


class TestEnabledFilter:
    def test_keeps_only_listed_projects(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        (tree["projects"] / "Other" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=["Demo"])
        result = _run(["rescan"], tree["env"])
        assert "Found 1 project" in result.stdout
        assert [p["name"] for p in _cache(tree["home"])["projects"]] == ["Demo"]

    def test_selector_matches_nested_rel_path(self, tree):
        (tree["projects"] / "group" / "nested-app" / ".git").mkdir(parents=True)
        (tree["projects"] / "Other" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=["group/nested-app"])
        _run(["rescan"], tree["env"])
        assert [p["rel"] for p in _cache(tree["home"])["projects"]] == ["group/nested-app"]

    def test_unmatched_selector_warns(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=["Nope"])
        result = _run(["rescan"], tree["env"])
        assert "Nope" in result.stderr

    def test_empty_list_keeps_all_candidates(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        (tree["projects"] / "Other" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=[])
        _run(["rescan"], tree["env"])
        assert len(_cache(tree["home"])["projects"]) == 2


class TestBootstrap:
    def test_enables_pack_yml_members_only(self, tree):
        member = tree["projects"] / "Member"
        (member / ".opskit").mkdir(parents=True)
        (member / ".opskit" / "pack.yml").write_text("contract: 1\nname: member\n")
        (tree["projects"] / "JustGit" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=[])
        result = _run(["bootstrap"], tree["env"])
        assert result.returncode == 0, result.stderr
        assert _cfg(tree["home"])["projects"] == ["Member"]
        assert [p["name"] for p in _cache(tree["home"])["projects"]] == ["member"]


class TestConfigManagedList:
    def test_add_appends_selector_and_rescans(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        (tree["projects"] / "Other" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=["Demo"])
        result = _run(["add", str(tree["projects"] / "Other")], tree["env"])
        assert result.returncode == 0, result.stderr
        assert "Other" in _cfg(tree["home"])["projects"]
        names = {p["name"] for p in _cache(tree["home"])["projects"]}
        assert names == {"Demo", "Other"}

    def test_remove_drops_selector(self, tree):
        (tree["projects"] / "Demo" / ".git").mkdir(parents=True)
        (tree["projects"] / "Other" / ".git").mkdir(parents=True)
        _write_config(tree["home"], tree["projects"], projects=["Demo", "Other"])
        _run(["rescan"], tree["env"])
        result = _run(["remove", "Other"], tree["env"])
        assert result.returncode == 0, result.stderr
        assert _cfg(tree["home"])["projects"] == ["Demo"]
        assert [p["name"] for p in _cache(tree["home"])["projects"]] == ["Demo"]
