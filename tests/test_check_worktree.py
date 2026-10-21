"""Tests for bin/check-worktree.sh — primary-checkout detection (issue #450).

The script guards the repo rule that the primary checkout stays on `main` and all
development happens in a linked worktree. Its detection used to derive a "primary
path" from the script's own location and compare it against each entry of
`git worktree list`, which always matched the worktree the caller was standing
in: every worktree commit printed "in the primary checkout", and the one case
worth catching (primary checkout left on a feature branch) became
indistinguishable from routine noise.

These tests build real repositories — the defect is in how git itself is
queried, so a stubbed git would reproduce the bug's assumptions instead of
catching them.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "check-worktree.sh"

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid"]


def git(*args: str, cwd: Path) -> str:
    """Run git with identity pinned, so no ambient config can change results."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        [*GIT, *args], cwd=cwd, capture_output=True, text=True, env=env
    )
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr}"
    return proc.stdout


def make_repo(tmp_path: Path, branch: str = "main") -> Path:
    repo = tmp_path / "primary"
    repo.mkdir()
    git("init", f"--initial-branch={branch}", cwd=repo)
    git("commit", "--allow-empty", "-m", "initial", cwd=repo)
    return repo


def add_worktree(repo: Path, path: str, branch: str) -> Path:
    wt = repo.parent / path
    git("worktree", "add", "-b", branch, str(wt), cwd=repo)
    return wt


def run(cwd: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *flags], cwd=cwd, capture_output=True, text=True
    )


def test_worktree_feature_branch_is_not_the_primary_checkout(tmp_path: Path):
    """The #450 regression: a worktree commit must not claim to be primary."""
    repo = make_repo(tmp_path)
    wt = add_worktree(repo, "wt-feature", "some-feature")

    result = run(wt)

    assert result.returncode == 0
    assert "primary checkout" not in result.stdout
    assert "In worktree" in result.stdout
    assert "some-feature" in result.stdout


def test_worktree_with_space_in_path(tmp_path: Path):
    """Path comparison used to word-split; git's own resolution must not care."""
    repo = make_repo(tmp_path)
    wt = add_worktree(repo, "wt with space", "spacey")

    result = run(wt)

    assert result.returncode == 0
    assert "primary checkout" not in result.stdout
    assert "In worktree" in result.stdout


def test_worktree_from_subdirectory(tmp_path: Path):
    """Detection must hold from anywhere inside the worktree, not just its root."""
    repo = make_repo(tmp_path)
    wt = add_worktree(repo, "wt-sub", "sub-feature")
    nested = wt / "deep" / "dir"
    nested.mkdir(parents=True)

    result = run(nested)

    assert result.returncode == 0
    assert "primary checkout" not in result.stdout
    assert "In worktree" in result.stdout


def test_primary_checkout_on_main_is_blocked(tmp_path: Path):
    repo = make_repo(tmp_path)

    result = run(repo)

    assert result.returncode == 1
    assert "Refusing to commit on main in the primary checkout" in result.stdout


def test_primary_checkout_on_main_allows_explicit_override(tmp_path: Path):
    repo = make_repo(tmp_path)

    result = run(repo, "--allow-main")

    assert result.returncode == 0
    assert "Override acknowledged" in result.stdout


def test_primary_checkout_on_feature_branch_warns(tmp_path: Path):
    """The genuine condition the script exists to flag must still fire."""
    repo = make_repo(tmp_path)
    git("checkout", "-b", "stray-feature", cwd=repo)

    result = run(repo)

    assert result.returncode == 0
    assert "in the primary checkout" in result.stdout
    assert "stray-feature" in result.stdout


def test_worktree_on_main_warns_about_the_worktree(tmp_path: Path):
    """A worktree on `main` is a distinct case and must not be called primary."""
    # Git refuses to check out the same branch twice, so the primary sits on a
    # different branch and the worktree takes `main`.
    repo = make_repo(tmp_path, branch="develop")
    wt = add_worktree(repo, "wt-main", "main")

    result = run(wt)

    assert result.returncode == 0
    assert "primary checkout" not in result.stdout
    assert "is on branch 'main'" in result.stdout


def test_outside_a_git_repository(tmp_path: Path):
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = run(outside)

    assert result.returncode == 1
    assert "not inside a git repository" in result.stdout + result.stderr
