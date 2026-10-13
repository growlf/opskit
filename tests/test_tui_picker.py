"""Tests for the bin/opskit-go.py fzf picker layout (issue #442).

Loads the real script as a module so tests exercise the shipped code.
"""

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


def _load_go_module():
    spec = importlib.util.spec_from_file_location(
        "opskit_go_picker", _ROOT / "bin" / "opskit-go.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_go = _load_go_module()


class _Proc:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def _fake_run(returncode, stdout, captured):
    def fake(*args, **kwargs):
        captured["argv"] = args[0]
        captured["kwargs"] = kwargs
        return _Proc(returncode, stdout)
    return fake


PROJECTS = [
    {"name": "Demo", "path": "/home/user/Projects/Demo", "rel": "Demo"},
    {"name": "app", "path": "/home/user/Projects/group/app", "rel": "group/app"},
]


class TestPickerHeader:
    def test_header_names_the_columns(self):
        header = _go._picker_header()
        for col in ("NAME", "BRANCH", "STATUS", "RESUME"):
            assert col in header


class TestPickerRow:
    def test_columns_align_with_header(self):
        header = _go._picker_header()
        row = _go._picker_row(
            {"name": "Demo", "path": "/p/Demo", "rel": "Demo", "has_resume": True},
            git_lookup=lambda _p: ("main", "dirty"),
        )
        assert header.index("BRANCH") == row.index("main")
        assert header.index("STATUS") == row.index("dirty")
        assert header.index("RESUME") == row.index("[resume]")

    def test_clean_project_has_no_resume_flag(self):
        row = _go._picker_row(
            {"name": "Demo", "path": "/p/Demo", "rel": "Demo"},
            git_lookup=lambda _p: ("main", "clean"),
        )
        assert "clean" in row
        assert "[resume]" not in row

    def test_long_name_is_truncated_to_column_width(self):
        row = _go._picker_row(
            {"name": "x", "path": "/p/x", "rel": "a" * 60},
            git_lookup=lambda _p: ("main", "clean"),
        )
        name_col = row[: _go.PICKER_NAME_W]
        assert len(name_col) == _go.PICKER_NAME_W
        assert "…" in name_col


class TestBuildPicker:
    def test_line_field_one_is_the_path(self):
        _header, lines = _go.build_picker(PROJECTS, git_lookup=lambda _p: ("main", "clean"))
        assert lines[0].split("\t")[0] == "/home/user/Projects/Demo"
        assert lines[1].split("\t")[0] == "/home/user/Projects/group/app"

    def test_one_line_per_project(self):
        _header, lines = _go.build_picker(PROJECTS, git_lookup=lambda _p: ("main", "clean"))
        assert len(lines) == len(PROJECTS)

    def test_git_lookup_is_used_for_branch_and_status(self):
        _header, lines = _go.build_picker(PROJECTS, git_lookup=lambda _p: ("feature/x", "dirty"))
        assert "feature/x" in lines[0]
        assert "dirty" in lines[0]


class TestRunFzfSelection:
    def test_no_timeout_and_column_options(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(_go, "_git_info", lambda _p: ("main", "clean"))
        monkeypatch.setattr(_go.subprocess, "run", _fake_run(0, PROJECTS[0]["path"] + "\n", captured))

        selected = _go.run_fzf_selection(PROJECTS)

        assert "timeout" not in captured["kwargs"]
        argv = captured["argv"]
        assert "--delimiter=\t" in argv
        assert "--with-nth=2" in argv
        assert "--accept-nth=1" in argv
        assert any(a.startswith("--header=") for a in argv)
        assert selected == PROJECTS[0]["path"]

    def test_cancel_returns_none(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(_go, "_git_info", lambda _p: ("main", "clean"))
        monkeypatch.setattr(_go.subprocess, "run", _fake_run(130, "", captured))

        assert _go.run_fzf_selection(PROJECTS) is None

    def test_empty_selection_returns_none(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(_go, "_git_info", lambda _p: ("main", "clean"))
        monkeypatch.setattr(_go.subprocess, "run", _fake_run(0, "\n", captured))

        assert _go.run_fzf_selection(PROJECTS) is None
