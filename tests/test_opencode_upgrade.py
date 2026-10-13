"""Tests for the opskit go pre-launch opencode upgrade check (issue #444).

Loads the real bin/opskit-go.py as a module so tests hit the shipped code,
and imports opskit._opencode / opskit._cache directly.
"""

import importlib.util
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from opskit import _cache, _opencode


def _load_go_module():
    spec = importlib.util.spec_from_file_location(
        "opskit_go_upgrade", _ROOT / "bin" / "opskit-go.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_go = _load_go_module()


class _Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


LS_REMOTE = (
    "aaaa\trefs/tags/v2.0.27\n"
    "bbbb\trefs/tags/v2.0.28\n"
    "cccc\trefs/tags/v2.0.28^{}\n"
    "dddd\trefs/tags/vscode-v1.0.0\n"
    "eeee\trefs/tags/v2.1.0\n"
    "ffff\trefs/tags/not-a-version\n"
)


def _raise(*_a, **_k):
    raise AssertionError("should not be called")


class TestVersionParsing:
    def test_parse_opencode_version_banner(self):
        assert _opencode.parse_version("opencode v2.0.28") == (2, 0, 28)

    def test_parse_version_missing_returns_none(self):
        assert _opencode.parse_version("") is None
        assert _opencode.parse_version("no version here") is None

    @pytest.mark.parametrize(
        "latest,installed,expected",
        [
            ("2.1.0", "2.0.28", True),
            ("2.0.28", "2.0.28", False),
            ("1.19.0", "2.0.28", False),
        ],
    )
    def test_is_newer(self, latest, installed, expected):
        assert _opencode.is_newer(latest, installed) is expected


class TestTagParsing:
    def test_picks_highest_semver_tag(self):
        assert _opencode.parse_latest_tag(LS_REMOTE) == "2.1.0"

    def test_ignores_vscode_and_peeled_tags(self):
        out = "x\trefs/tags/vscode-v9.9.9\ny\trefs/tags/v1.2.3^{}\n"
        assert _opencode.parse_latest_tag(out) is None

    def test_empty_output_returns_none(self):
        assert _opencode.parse_latest_tag("") is None


class TestInstalledVersion:
    def test_reads_opencode_version(self):
        runner = lambda *a, **k: _Result(stdout="opencode v2.0.28\n")
        assert _opencode.get_installed_version(runner=runner) == "2.0.28"

    def test_missing_opencode_returns_none(self):
        def boom(*a, **k):
            raise FileNotFoundError

        assert _opencode.get_installed_version(runner=boom) is None


class TestLatestDevVersion:
    def test_uses_git_ls_remote(self):
        seen = {}

        def runner(argv, *a, **k):
            seen["argv"] = argv
            return _Result(stdout=LS_REMOTE)

        assert _opencode.get_latest_dev_version(repo="o/r", runner=runner) == "2.1.0"
        assert seen["argv"][:3] == ["git", "ls-remote", "--tags"]

    def test_offline_returns_none(self):
        def boom(*a, **k):
            raise OSError

        assert _opencode.get_latest_dev_version(runner=boom) is None


class TestCheckCache:
    def test_roundtrip_and_staleness(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_cache, "OPENCODE_CHECK_FILE", tmp_path / "check.json")
        assert _cache.read_opencode_check() is None

        data = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "installed": "2.0.28",
            "latest": "2.1.0",
        }
        _cache.write_opencode_check(data)
        assert _cache.read_opencode_check()["latest"] == "2.1.0"
        assert not _cache.opencode_check_is_stale(data, "2.0.28")

    def test_stale_when_installed_changed(self):
        data = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "installed": "2.0.28",
            "latest": "2.1.0",
        }
        assert _cache.opencode_check_is_stale(data, "2.0.29")

    def test_stale_when_old_or_missing(self):
        old = {
            "checked_at": "2000-01-01T00:00:00+00:00",
            "installed": "2.0.28",
            "latest": "2.1.0",
        }
        assert _cache.opencode_check_is_stale(old, "2.0.28")
        assert _cache.opencode_check_is_stale(None, "2.0.28")


def _wire(monkeypatch, *, tty=True, installed="2.0.28", cache=None, stale=True,
          answer="n"):
    """Patch the go module's collaborators for maybe_offer_opencode_upgrade."""
    monkeypatch.setattr(_go.sys, "stdin", types.SimpleNamespace(isatty=lambda: tty))
    monkeypatch.setattr(_go, "get_installed_version", lambda: installed)
    monkeypatch.setattr(_go, "read_opencode_check", lambda: cache)
    monkeypatch.setattr(_go, "opencode_check_is_stale", lambda d, i: stale)
    monkeypatch.setattr(_go, "write_opencode_check", lambda d: None)
    monkeypatch.setattr("builtins.input", lambda *a: answer)

    calls = {}

    def fake_run(argv, *a, **k):
        calls["argv"] = argv
        return _Result(returncode=0)

    monkeypatch.setattr(_go.subprocess, "run", fake_run)
    return calls


class TestMaybeOfferUpgrade:
    def test_non_tty_skips_everything(self, monkeypatch):
        net = {"called": False}

        def latest(*a, **k):
            net["called"] = True
            return "2.1.0"

        _wire(monkeypatch, tty=False)
        monkeypatch.setattr(_go, "get_latest_dev_version", latest)
        monkeypatch.setattr("builtins.input", _raise)
        _go.maybe_offer_opencode_upgrade()
        assert net["called"] is False

    def test_offline_is_silent(self, monkeypatch, capsys):
        _wire(monkeypatch, cache=None, stale=True)
        monkeypatch.setattr(_go, "get_latest_dev_version", lambda *a, **k: None)
        monkeypatch.setattr("builtins.input", _raise)
        _go.maybe_offer_opencode_upgrade()
        assert "available" not in capsys.readouterr().out

    def test_fresh_cache_skips_network(self, monkeypatch):
        cache = {
            "checked_at": "2020-01-01T00:00:00+00:00",
            "installed": "2.0.28",
            "latest": "2.1.0",
        }
        calls = _wire(monkeypatch, cache=cache, stale=False, answer="n")
        monkeypatch.setattr(_go, "get_latest_dev_version", _raise)
        _go.maybe_offer_opencode_upgrade()
        assert "argv" not in calls

    def test_no_newer_version_does_not_prompt(self, monkeypatch):
        _wire(monkeypatch, cache=None, stale=True)
        monkeypatch.setattr(_go, "get_latest_dev_version", lambda *a, **k: "2.0.28")
        monkeypatch.setattr("builtins.input", _raise)
        _go.maybe_offer_opencode_upgrade()

    def test_accept_runs_opencode_upgrade(self, monkeypatch):
        calls = _wire(monkeypatch, cache=None, stale=True, answer="y")
        monkeypatch.setattr(_go, "get_latest_dev_version", lambda *a, **k: "2.1.0")
        _go.maybe_offer_opencode_upgrade()
        assert calls["argv"] == ["opencode", "upgrade"]

    def test_decline_does_not_upgrade(self, monkeypatch):
        calls = _wire(monkeypatch, cache=None, stale=True, answer="n")
        monkeypatch.setattr(_go, "get_latest_dev_version", lambda *a, **k: "2.1.0")
        _go.maybe_offer_opencode_upgrade()
        assert "argv" not in calls


class TestLaunchHandoffMessage:
    def test_message_printed_before_exec(self, monkeypatch, capsys):
        monkeypatch.setattr(_go, "run_openskill_setup", lambda: None)
        monkeypatch.setattr(_go, "get_bw_session", lambda: "")
        monkeypatch.setattr(_go, "update_last_used", lambda p: None)
        monkeypatch.setattr(_go.os, "chdir", lambda p: None)

        def fake_exec(*a, **k):
            raise SystemExit(0)

        monkeypatch.setattr(_go.os, "execvpe", fake_exec)
        with pytest.raises(SystemExit):
            _go.launch_project("/tmp/project")
        assert "Now starting interactive OpenCode shell" in capsys.readouterr().out
